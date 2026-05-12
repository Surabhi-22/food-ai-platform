// User / Vendor Types
export interface Vendor {
  id: string;
  business_name: string;
  email: string;
  logo_url?: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Menu Items
export interface MenuItem {
  id: string;
  vendor_id: string;
  name: string;
  description?: string;
  category: string;
  price: number;
  cogs_percentage?: number;
  is_active: boolean;
  created_at: string;
}

// Orders
export interface OrderItem {
  id: string;
  order_id: string;
  menu_item_id: string;
  quantity: number;
  unit_price: number;
  menu_item_name?: string;
}

export interface Order {
  id: string;
  vendor_id: string;
  customer_id?: string;
  status: "pending" | "preparing" | "ready" | "completed" | "cancelled";
  total_amount: number;
  created_at: string;
  updated_at: string;
  items: OrderItem[];
}

// Forecasts
export interface ForecastItem {
  menu_item_id: string;
  menu_item_name: string;
  category: string;
  forecast_date: string;
  predicted_quantity: number;
  predicted_revenue: number;
  predicted_profit: number;
  confidence_lower: number;
  confidence_upper: number;
  cluster_label: string;
  inventory_required: number;
  model_version: string;
}

export interface ForecastDateGroup {
  forecast_date: string;
  items: ForecastItem[];
  total_predicted_quantity: number;
  total_predicted_revenue: number;
}

export interface ForecastListResponse {
  vendor_id: string;
  forecast_groups: ForecastDateGroup[];
  total_items: number;
  date_range_start: string;
  date_range_end: string;
  cached: boolean;
}

export interface LowStockAlert {
  menu_item_id: string;
  menu_item_name: string;
  category: string;
  predicted_demand_3day: number;
  avg_daily_supply: number;
  deficit: number;
  severity: "high" | "medium" | "low";
}

export interface ForecastSummaryResponse {
  vendor_id: string;
  total_revenue_3day: number;
  total_profit_3day: number;
  total_quantity_3day: number;
  top_item: ForecastItem | null;
  low_stock_alerts: LowStockAlert[];
  model_version: string;
  forecast_generated_at: string | null;
  cached: boolean;
}

// Analytics
export interface RevenueDaily {
  date: string;
  revenue: number;
  order_count: number;
}

export interface TopItem {
  menu_item_id: string;
  name: string;
  total_quantity: number;
  total_revenue: number;
}
