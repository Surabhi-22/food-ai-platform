-- ============================================================================
-- Migration 001: Create all tables for Food Demand Forecasting Platform
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── ENUM Types ──────────────────────────────────────────────────────────────

CREATE TYPE order_status AS ENUM ('pending', 'confirmed', 'cancelled');
CREATE TYPE ml_run_status AS ENUM ('pending', 'running', 'completed', 'failed');

-- ── Vendors ─────────────────────────────────────────────────────────────────

CREATE TABLE vendors (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_name VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    logo_url    TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_vendors_email ON vendors(email);

-- ── Customers ───────────────────────────────────────────────────────────────

CREATE TABLE customers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id   UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    phone       VARCHAR(20),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_customers_vendor_id ON customers(vendor_id);
CREATE INDEX idx_customers_email ON customers(email);

-- ── Menu Items ──────────────────────────────────────────────────────────────

CREATE TABLE menu_items (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id       UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    category        VARCHAR(100) NOT NULL,
    price           NUMERIC(10, 2) NOT NULL CHECK (price > 0),
    cogs_percentage NUMERIC(5, 2) NOT NULL DEFAULT 30.00 CHECK (cogs_percentage >= 0 AND cogs_percentage <= 100),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_menu_items_vendor_id ON menu_items(vendor_id);
CREATE INDEX idx_menu_items_category ON menu_items(category);
CREATE INDEX idx_menu_items_vendor_active ON menu_items(vendor_id, is_active);

-- ── Orders ──────────────────────────────────────────────────────────────────

CREATE TABLE orders (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id     UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    customer_id   UUID REFERENCES customers(id) ON DELETE SET NULL,
    status        order_status NOT NULL DEFAULT 'pending',
    total_amount  NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_orders_vendor_id ON orders(vendor_id);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_vendor_created ON orders(vendor_id, created_at DESC);
CREATE INDEX idx_orders_vendor_status ON orders(vendor_id, status);

-- ── Order Items ─────────────────────────────────────────────────────────────

CREATE TABLE order_items (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id      UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id  UUID REFERENCES menu_items(id) ON DELETE SET NULL,
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(10, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_menu_item_id ON order_items(menu_item_id);

-- ── Forecasts ───────────────────────────────────────────────────────────────

CREATE TABLE forecasts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id           UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    menu_item_id        UUID NOT NULL REFERENCES menu_items(id) ON DELETE CASCADE,
    forecast_date       DATE NOT NULL,
    predicted_quantity  NUMERIC(10, 2) NOT NULL,
    predicted_revenue   NUMERIC(12, 2) NOT NULL,
    confidence_lower    NUMERIC(10, 2) NOT NULL,
    confidence_upper    NUMERIC(10, 2) NOT NULL,
    model_version       VARCHAR(50) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_forecasts_vendor_id ON forecasts(vendor_id);
CREATE INDEX idx_forecasts_menu_item_id ON forecasts(menu_item_id);
CREATE INDEX idx_forecasts_date ON forecasts(forecast_date);
CREATE INDEX idx_forecasts_vendor_date ON forecasts(vendor_id, forecast_date);

-- ── Chat Sessions ───────────────────────────────────────────────────────────

CREATE TABLE chat_sessions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id   UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    messages    JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_vendor_id ON chat_sessions(vendor_id);
CREATE INDEX idx_chat_sessions_messages ON chat_sessions USING GIN (messages);

-- ── ML Run Logs ─────────────────────────────────────────────────────────────

CREATE TABLE ml_run_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id   UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    model_type  VARCHAR(50) NOT NULL,
    rmse        NUMERIC(10, 4),
    mae         NUMERIC(10, 4),
    mape        NUMERIC(10, 4),
    trained_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status      ml_run_status NOT NULL DEFAULT 'pending'
);

CREATE INDEX idx_ml_run_logs_vendor_id ON ml_run_logs(vendor_id);
CREATE INDEX idx_ml_run_logs_status ON ml_run_logs(status);

-- ── Updated_at Trigger Function ─────────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
CREATE TRIGGER set_updated_at_vendors
    BEFORE UPDATE ON vendors FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_updated_at_customers
    BEFORE UPDATE ON customers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_updated_at_menu_items
    BEFORE UPDATE ON menu_items FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_updated_at_orders
    BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_updated_at_forecasts
    BEFORE UPDATE ON forecasts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER set_updated_at_chat_sessions
    BEFORE UPDATE ON chat_sessions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
