"""
train_model.py
==============
Food Demand Forecasting — Random Forest Regressor
--------------------------------------------------
Dataset  : food_demand.csv
Target   : num_orders (daily demand per meal / fulfillment centre)
Saved    : model.pkl  (joblib)

Usage
-----
    python train_model.py

FastAPI integration
-------------------
    import joblib
    model = joblib.load("model.pkl")
    prediction = model.predict([[week, meal_id, checkout_price,
                                  base_price, emailer, homepage]])
"""

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error


# ─────────────────────────────────────────────
# 1. Load Dataset
# ─────────────────────────────────────────────

print("Loading dataset...")
df = pd.read_csv("food_demand.csv")

print(f"  Rows   : {len(df)}")
print(f"  Columns: {list(df.columns)}")


# ─────────────────────────────────────────────
# 2. Handle Missing Values
# ─────────────────────────────────────────────

df.fillna(0, inplace=True)
print("\nMissing values filled with 0.")


# ─────────────────────────────────────────────
# 3. Select Features & Target
# ─────────────────────────────────────────────

FEATURES = [
    "week",
    "meal_id",
    "checkout_price",
    "base_price",
    "emailer_for_promotion",
    "homepage_featured",
]

TARGET = "num_orders"

X = df[FEATURES]
y = df[TARGET]

print(f"\nFeatures : {FEATURES}")
print(f"Target   : {TARGET}")


# ─────────────────────────────────────────────
# 4. Train / Test Split  (80 % train, 20 % test)
# ─────────────────────────────────────────────

X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.20,
    random_state=42,
)

print(f"\nTrain samples : {len(X_train)}")
print(f"Test  samples : {len(X_test)}")


# ─────────────────────────────────────────────
# 5. Train Model — Random Forest Regressor
# ─────────────────────────────────────────────

print("\nTraining Random Forest Regressor ...")

model = RandomForestRegressor(
    n_estimators=100,   # number of trees
    max_depth=10,       # limits tree depth to avoid overfitting
    random_state=42,    # reproducibility
    n_jobs=-1,          # use all CPU cores
)

model.fit(X_train, y_train)
print("Training complete!")


# ─────────────────────────────────────────────
# 6. Evaluate — Mean Absolute Error (MAE)
# ─────────────────────────────────────────────

y_pred = model.predict(X_test)
mae = mean_absolute_error(y_test, y_pred)

print(f"\n{'='*40}")
print(f"  Mean Absolute Error (MAE) : {mae:.2f} orders")
print(f"{'='*40}")

# ─── Feature Importance (bonus — helpful for FastAPI response) ────────────────
importance = dict(zip(FEATURES, model.feature_importances_))
importance_sorted = sorted(importance.items(), key=lambda x: x[1], reverse=True)

print("\nFeature Importances (highest to lowest):")
for feat, score in importance_sorted:
    print(f"  {feat:<25} {score:.4f}")


# ─────────────────────────────────────────────
# 7. Save Model with joblib
# ─────────────────────────────────────────────

MODEL_PATH = "model.pkl"
joblib.dump(model, MODEL_PATH)
print(f"\nModel saved to: {MODEL_PATH}")


# ─────────────────────────────────────────────
# 8. Prediction Function
#    (drop this function into your FastAPI route)
# ─────────────────────────────────────────────

def predict_demand(
    week: int,
    meal_id: int,
    checkout_price: float,
    base_price: float,
    emailer_for_promotion: int,   # 0 or 1
    homepage_featured: int,       # 0 or 1
    model_path: str = "model.pkl",
) -> float:
    """
    Predict food demand (num_orders) for one scenario.

    Parameters
    ----------
    week                  : Calendar week number (e.g. 1–145)
    meal_id               : Unique meal identifier
    checkout_price        : Actual price customer pays
    base_price            : MRP / list price
    emailer_for_promotion : 1 if meal is featured in promo email, else 0
    homepage_featured     : 1 if meal appears on homepage, else 0
    model_path            : Path to the saved model.pkl file

    Returns
    -------
    float : Predicted number of orders (rounded to nearest whole number)

    FastAPI usage example
    ---------------------
        from fastapi import FastAPI
        from pydantic import BaseModel
        import joblib

        app = FastAPI()
        model = joblib.load("model.pkl")

        class PredictRequest(BaseModel):
            week: int
            meal_id: int
            checkout_price: float
            base_price: float
            emailer_for_promotion: int
            homepage_featured: int

        @app.post("/predict")
        def predict(req: PredictRequest):
            features = [[req.week, req.meal_id, req.checkout_price,
                         req.base_price, req.emailer_for_promotion,
                         req.homepage_featured]]
            prediction = model.predict(features)[0]
            return {"predicted_orders": round(float(prediction), 2)}
    """
    loaded_model = joblib.load(model_path)

    input_features = [[
        week,
        meal_id,
        checkout_price,
        base_price,
        emailer_for_promotion,
        homepage_featured,
    ]]

    prediction = loaded_model.predict(input_features)[0]
    return round(float(prediction), 2)


# ─────────────────────────────────────────────
# 9. Sample Test Prediction
# ─────────────────────────────────────────────

print("\n" + "="*40)
print("  SAMPLE PREDICTION TEST")
print("="*40)

sample_prediction = predict_demand(
    week=100,
    meal_id=1885,
    checkout_price=146.0,
    base_price=152.0,
    emailer_for_promotion=0,
    homepage_featured=0,
)

print(f"  Week                  : 100")
print(f"  Meal ID               : 1885")
print(f"  Checkout Price        : Rs. 146.00")
print(f"  Base Price            : Rs. 152.00")
print(f"  Emailer Promotion     : No")
print(f"  Homepage Featured     : No")
print(f"  Predicted Orders      : {sample_prediction}")
print("="*40)
print("\nDone! Model is ready for FastAPI integration.")
