export interface User {
  id: string;
  email: string;
  role: string;
  name?: string;
  restaurant_name?: string;
}

export interface MenuItem {
  id: string;
  name: string;
  description?: string;
  price: number;
  category: string;
  is_available: boolean;
  image_url?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Order {
  id: string;
  status: "pending" | "preparing" | "ready" | "completed" | "cancelled";
  total_amount: number;
  items: Array<{
    menu_item_id: string;
    quantity: number;
    price: number;
    name?: string;
  }>;
  created_at: string;
}

export interface Prediction {
  date: string;
  predicted_demand: number;
  quantity?: number; // Fallback for some API endpoints
  confidence_score: number;
  factors: Record<string, unknown>;
}

export interface DashboardAnalytics {
  total_revenue_3day: number;
  total_quantity_3day: number;
  low_stock_alerts: Array<{
    item_name: string;
    current_stock: number;
    predicted_demand: number;
    unit: string;
  }>;
  top_item: {
    menu_item_name: string;
    predicted_quantity: number;
  };
}

export interface InventoryItem {
  id: string;
  ingredient_name: string;
  current_stock: number;
  unit: string;
  reorder_level: number;
  cost_per_unit: number;
  last_restocked: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  size: number;
}
