import { api } from "@/lib/api";
import { InventoryItem, PaginatedResponse } from "@/types/api";

export const InventoryService = {
  // GET /api/v1/analytics/inventory
  // Returns { items: [{ menu_item_id, item_name, category, predicted_demand, actual_sales, delta }], ... }
  getInventory: async (params?: Record<string, unknown>): Promise<Record<string, unknown>> => {
    const response = await api.get("/analytics/inventory", { params });
    return response.data;
  },

  updateStock: async (_id: string, _quantity: number): Promise<void> => {
    // No dedicated /inventory PATCH endpoint in backend — stock is managed via orders
    return Promise.resolve();
  },

  addInventoryItem: async (_data: unknown): Promise<void> => {
    // No dedicated /inventory POST endpoint in backend
    return Promise.resolve();
  },
};
