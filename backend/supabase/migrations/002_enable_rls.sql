-- ============================================================================
-- Migration 002: Enable Row-Level Security on all tables
-- Vendors can only access their own data.
-- ============================================================================

-- ── Enable RLS on all tables ────────────────────────────────────────────────

ALTER TABLE vendors ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE forecasts ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE ml_run_logs ENABLE ROW LEVEL SECURITY;

-- ── Vendors: can only read/update their own row ─────────────────────────────

CREATE POLICY vendor_select_own ON vendors
    FOR SELECT USING (id = auth.uid());

CREATE POLICY vendor_update_own ON vendors
    FOR UPDATE USING (id = auth.uid())
    WITH CHECK (id = auth.uid());

-- ── Customers: vendor can only access their own customers ───────────────────

CREATE POLICY customer_select_own ON customers
    FOR SELECT USING (vendor_id = auth.uid());

CREATE POLICY customer_insert_own ON customers
    FOR INSERT WITH CHECK (vendor_id = auth.uid());

CREATE POLICY customer_update_own ON customers
    FOR UPDATE USING (vendor_id = auth.uid())
    WITH CHECK (vendor_id = auth.uid());

CREATE POLICY customer_delete_own ON customers
    FOR DELETE USING (vendor_id = auth.uid());

-- ── Menu Items: vendor can only access their own items ──────────────────────

CREATE POLICY menu_item_select_own ON menu_items
    FOR SELECT USING (vendor_id = auth.uid());

CREATE POLICY menu_item_insert_own ON menu_items
    FOR INSERT WITH CHECK (vendor_id = auth.uid());

CREATE POLICY menu_item_update_own ON menu_items
    FOR UPDATE USING (vendor_id = auth.uid())
    WITH CHECK (vendor_id = auth.uid());

CREATE POLICY menu_item_delete_own ON menu_items
    FOR DELETE USING (vendor_id = auth.uid());

-- ── Orders: vendor can only access their own orders ─────────────────────────

CREATE POLICY order_select_own ON orders
    FOR SELECT USING (vendor_id = auth.uid());

CREATE POLICY order_insert_own ON orders
    FOR INSERT WITH CHECK (vendor_id = auth.uid());

CREATE POLICY order_update_own ON orders
    FOR UPDATE USING (vendor_id = auth.uid())
    WITH CHECK (vendor_id = auth.uid());

CREATE POLICY order_delete_own ON orders
    FOR DELETE USING (vendor_id = auth.uid());

-- ── Order Items: access via parent order's vendor_id ────────────────────────

CREATE POLICY order_item_select_own ON order_items
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM orders
            WHERE orders.id = order_items.order_id
            AND orders.vendor_id = auth.uid()
        )
    );

CREATE POLICY order_item_insert_own ON order_items
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM orders
            WHERE orders.id = order_items.order_id
            AND orders.vendor_id = auth.uid()
        )
    );

CREATE POLICY order_item_update_own ON order_items
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM orders
            WHERE orders.id = order_items.order_id
            AND orders.vendor_id = auth.uid()
        )
    );

CREATE POLICY order_item_delete_own ON order_items
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM orders
            WHERE orders.id = order_items.order_id
            AND orders.vendor_id = auth.uid()
        )
    );

-- ── Forecasts: vendor can only access their own forecasts ───────────────────

CREATE POLICY forecast_select_own ON forecasts
    FOR SELECT USING (vendor_id = auth.uid());

CREATE POLICY forecast_insert_own ON forecasts
    FOR INSERT WITH CHECK (vendor_id = auth.uid());

CREATE POLICY forecast_update_own ON forecasts
    FOR UPDATE USING (vendor_id = auth.uid())
    WITH CHECK (vendor_id = auth.uid());

CREATE POLICY forecast_delete_own ON forecasts
    FOR DELETE USING (vendor_id = auth.uid());

-- ── Chat Sessions: vendor can only access their own sessions ────────────────

CREATE POLICY chat_session_select_own ON chat_sessions
    FOR SELECT USING (vendor_id = auth.uid());

CREATE POLICY chat_session_insert_own ON chat_sessions
    FOR INSERT WITH CHECK (vendor_id = auth.uid());

CREATE POLICY chat_session_update_own ON chat_sessions
    FOR UPDATE USING (vendor_id = auth.uid())
    WITH CHECK (vendor_id = auth.uid());

CREATE POLICY chat_session_delete_own ON chat_sessions
    FOR DELETE USING (vendor_id = auth.uid());

-- ── ML Run Logs: vendor can only access their own logs ──────────────────────

CREATE POLICY ml_run_log_select_own ON ml_run_logs
    FOR SELECT USING (vendor_id = auth.uid());

CREATE POLICY ml_run_log_insert_own ON ml_run_logs
    FOR INSERT WITH CHECK (vendor_id = auth.uid());

-- ── Enable Supabase Realtime on orders table ────────────────────────────────

ALTER PUBLICATION supabase_realtime ADD TABLE orders;

-- ── Service role bypass for backend operations ──────────────────────────────
-- The backend uses service_role key which bypasses RLS.
-- These policies only apply to client-side Supabase calls using anon key.
