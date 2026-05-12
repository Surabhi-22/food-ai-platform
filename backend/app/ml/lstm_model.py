"""
LSTM demand forecasting model using Keras.

Builds a deep learning model for sequential time-series prediction
with 2 LSTM layers, dropout regularization, and early stopping.

Academic Reference:
    - LSTM for time-series forecasting (Hochreiter & Schmidhuber, 1997)
    - Dropout as regularization (Srivastava et al., 2014)
    - Sequence-to-one architecture for demand prediction (Bandara et al., 2020)
"""

import logging
import os
import pickle
from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error

from app.ml.features import FEATURE_COLUMNS, TARGET_COLUMN

logger = logging.getLogger(__name__)

# Suppress TensorFlow warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"

# Model artifact directory
MODEL_DIR = Path(__file__).parent / "artifacts" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── Default Hyperparameters ──────────────────────────────────────────────────

LSTM_PARAMS = {
    "sequence_length": 14,       # 14-day lookback window
    "lstm_units_1": 64,          # First LSTM layer units
    "lstm_units_2": 32,          # Second LSTM layer units
    "dropout_rate": 0.2,         # Dropout for regularization
    "dense_units": 16,           # Dense layer before output
    "learning_rate": 0.001,
    "batch_size": 32,
    "epochs": 100,
    "patience": 10,              # EarlyStopping patience
}


def _model_path(vendor_id: UUID) -> Path:
    """Return the file path for a vendor's LSTM model weights."""
    return MODEL_DIR / f"lstm_{vendor_id}.keras"


def _history_path(vendor_id: UUID) -> Path:
    """Return the file path for training history."""
    return MODEL_DIR / f"lstm_history_{vendor_id}.pkl"


def build_lstm_model(
    n_features: int,
    sequence_length: int = 14,
    params: dict | None = None,
):
    """
    Build a 2-layer LSTM model with Keras.

    Architecture:
        Input (sequence_length, n_features)
        → LSTM(64, return_sequences=True)
        → Dropout(0.2)
        → LSTM(32)
        → Dropout(0.2)
        → Dense(16, ReLU)
        → Dense(1, linear)

    Args:
        n_features: Number of input features per timestep.
        sequence_length: Length of input sequences.
        params: Optional hyperparameter overrides.

    Returns:
        Compiled Keras Sequential model.
    """
    import tensorflow as tf
    from tensorflow.keras.models import Sequential
    from tensorflow.keras.layers import LSTM, Dense, Dropout, Input
    from tensorflow.keras.optimizers import Adam

    if params is None:
        params = LSTM_PARAMS.copy()

    model = Sequential([
        Input(shape=(sequence_length, n_features)),
        LSTM(
            units=params.get("lstm_units_1", 64),
            return_sequences=True,
            name="lstm_1",
        ),
        Dropout(params.get("dropout_rate", 0.2), name="dropout_1"),
        LSTM(
            units=params.get("lstm_units_2", 32),
            return_sequences=False,
            name="lstm_2",
        ),
        Dropout(params.get("dropout_rate", 0.2), name="dropout_2"),
        Dense(
            params.get("dense_units", 16),
            activation="relu",
            name="dense_hidden",
        ),
        Dense(1, activation="linear", name="output"),
    ])

    model.compile(
        optimizer=Adam(learning_rate=params.get("learning_rate", 0.001)),
        loss="mse",
        metrics=["mae"],
    )

    logger.info(
        "Built LSTM model: %d params, seq_len=%d, features=%d",
        model.count_params(), sequence_length, n_features,
    )
    return model


def create_sequences(
    data: np.ndarray,
    target: np.ndarray,
    sequence_length: int = 14,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Create sliding window sequences for LSTM input.

    Converts a 2D feature matrix and 1D target vector into
    3D sequences of shape (n_samples, sequence_length, n_features)
    with corresponding target values.

    Args:
        data: Feature matrix of shape (n_timesteps, n_features).
        target: Target vector of shape (n_timesteps,).
        sequence_length: Number of timesteps per sequence.

    Returns:
        Tuple of (X_sequences, y_targets) arrays.
    """
    X, y = [], []
    for i in range(len(data) - sequence_length):
        X.append(data[i : i + sequence_length])
        y.append(target[i + sequence_length])

    X_arr = np.array(X, dtype=np.float32)
    y_arr = np.array(y, dtype=np.float32)

    logger.info(
        "Created %d sequences of length %d with %d features",
        len(X_arr), sequence_length, X_arr.shape[2] if len(X_arr) > 0 else 0,
    )
    return X_arr, y_arr


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Calculate Mean Absolute Percentage Error, excluding zeros."""
    mask = y_true != 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def train_lstm(
    df: pd.DataFrame,
    vendor_id: UUID,
    params: dict | None = None,
) -> dict:
    """
    Train an LSTM model for demand forecasting.

    Steps:
        1. Prepare feature matrix and target from DataFrame
        2. Create sliding window sequences (14-day lookback)
        3. Split into train/validation (80/20, preserving temporal order)
        4. Train with EarlyStopping callback
        5. Evaluate on validation set
        6. Save model weights

    Args:
        df: Feature-engineered DataFrame sorted by date.
        vendor_id: UUID of the vendor.
        params: Optional hyperparameter overrides.

    Returns:
        Dictionary containing:
            - model: Trained Keras model
            - metrics: {rmse, mae, mape}
            - training_history: Loss and metric history per epoch
    """
    import tensorflow as tf
    from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau

    if params is None:
        params = LSTM_PARAMS.copy()

    sequence_length = params.get("sequence_length", 14)

    # Prepare features and target
    available_features = [f for f in FEATURE_COLUMNS if f in df.columns]
    X_raw = df[available_features].values.astype(np.float32)
    y_raw = df[TARGET_COLUMN].values.astype(np.float32)

    # Replace any remaining NaN/inf values
    X_raw = np.nan_to_num(X_raw, nan=0.0, posinf=0.0, neginf=0.0)
    y_raw = np.nan_to_num(y_raw, nan=0.0)

    if len(X_raw) < sequence_length + 10:
        logger.warning(
            "Insufficient data for LSTM training (need >= %d, have %d)",
            sequence_length + 10, len(X_raw),
        )
        return {
            "model": None,
            "metrics": {"rmse": float("inf"), "mae": float("inf"), "mape": float("inf")},
            "training_history": {},
        }

    # Create sequences
    X_seq, y_seq = create_sequences(X_raw, y_raw, int(sequence_length))

    if len(X_seq) == 0:
        logger.warning("No sequences created — data too short")
        return {
            "model": None,
            "metrics": {"rmse": float("inf"), "mae": float("inf"), "mape": float("inf")},
            "training_history": {},
        }

    # Train/validation split (80/20, temporal order preserved)
    split_idx = int(len(X_seq) * 0.8)
    split_idx = max(split_idx, 1)  # Ensure at least 1 training sample

    X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
    y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]

    logger.info(
        "Train: %d sequences, Validation: %d sequences",
        len(X_train), len(X_val),
    )

    # Build model
    n_features = X_seq.shape[2]
    model = build_lstm_model(n_features, sequence_length, params)

    # Callbacks
    callbacks = [
        EarlyStopping(
            monitor="val_loss",
            patience=params.get("patience", 10),
            restore_best_weights=True,
            verbose=1,
        ),
        ReduceLROnPlateau(
            monitor="val_loss",
            factor=0.5,
            patience=5,
            min_lr=1e-6,
            verbose=1,
        ),
    ]

    # Train
    history = model.fit(
        X_train, y_train,
        validation_data=(X_val, y_val) if len(X_val) > 0 else None,
        epochs=params.get("epochs", 100),
        batch_size=params.get("batch_size", 32),
        callbacks=callbacks,
        verbose=0,
    )

    # Evaluate on validation set
    if len(X_val) > 0:
        y_pred = model.predict(X_val, verbose=0).flatten()
        y_pred = np.maximum(y_pred, 0)  # Demand cannot be negative

        metrics = {
            "rmse": float(np.sqrt(mean_squared_error(y_val, y_pred))),
            "mae": float(mean_absolute_error(y_val, y_pred)),
            "mape": calculate_mape(y_val, y_pred),
        }
    else:
        # Evaluate on training set if no validation data
        y_pred = model.predict(X_train, verbose=0).flatten()
        y_pred = np.maximum(y_pred, 0)
        metrics = {
            "rmse": float(np.sqrt(mean_squared_error(y_train, y_pred))),
            "mae": float(mean_absolute_error(y_train, y_pred)),
            "mape": calculate_mape(y_train, y_pred),
        }

    # Save model
    model.save(_model_path(vendor_id))
    logger.info("Saved LSTM model for vendor %s", vendor_id)

    # Save training history
    with open(_history_path(vendor_id), "wb") as f:
        pickle.dump(history.history, f)

    logger.info(
        "LSTM training complete — RMSE: %.4f, MAE: %.4f, MAPE: %.2f%%",
        metrics["rmse"], metrics["mae"], metrics["mape"],
    )

    return {
        "model": model,
        "metrics": metrics,
        "training_history": history.history,
    }


def predict_lstm(
    vendor_id: UUID,
    X_sequences: np.ndarray,
) -> np.ndarray:
    """
    Generate predictions using a trained LSTM model.

    Args:
        vendor_id: UUID of the vendor.
        X_sequences: 3D array of shape (n_samples, sequence_length, n_features).

    Returns:
        Array of predicted demand quantities (clipped to >= 0).
    """
    import tensorflow as tf

    model_path = _model_path(vendor_id)
    if not model_path.exists():
        raise FileNotFoundError(f"No trained LSTM model found for vendor {vendor_id}")

    model = tf.keras.models.load_model(model_path)
    predictions = model.predict(X_sequences, verbose=0).flatten()
    return np.maximum(predictions, 0)
