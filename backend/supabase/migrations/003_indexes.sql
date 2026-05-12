-- ============================================================================
-- Migration 003: Additional composite indexes for query optimization
-- ============================================================================

-- ── Analytics query optimization ────────────────────────────────────────────

-- Revenue analytics: vendor + status + date for daily revenue queries
CREATE INDEX IF NOT EXISTS idx_orders_vendor_status_date
    ON orders(vendor_id, status, created_at DESC);

-- Top items: join optimization for order_items → orders → menu_items
CREATE INDEX IF NOT EXISTS idx_order_items_menu_quantity
    ON order_items(menu_item_id, quantity);

-- ── Forecast query optimization ─────────────────────────────────────────────

-- Vendor + item + date range queries
CREATE INDEX IF NOT EXISTS idx_forecasts_vendor_item_date
    ON forecasts(vendor_id, menu_item_id, forecast_date);

-- ── Menu item lookup optimization ───────────────────────────────────────────

-- Vendor + category + active status for filtered menu queries
CREATE INDEX IF NOT EXISTS idx_menu_items_vendor_category_active
    ON menu_items(vendor_id, category, is_active);

-- ── Chat session optimization ───────────────────────────────────────────────

-- Vendor + updated_at for recent sessions
CREATE INDEX IF NOT EXISTS idx_chat_sessions_vendor_updated
    ON chat_sessions(vendor_id, updated_at DESC);

-- ── ML run logs optimization ────────────────────────────────────────────────

-- Vendor + status + trained_at for latest runs
CREATE INDEX IF NOT EXISTS idx_ml_run_logs_vendor_status_date
    ON ml_run_logs(vendor_id, status, trained_at DESC);
