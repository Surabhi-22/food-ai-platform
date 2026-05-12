import { api } from "@/lib/api";
import { Order, PaginatedResponse } from "@/types/api";

export const OrdersService = {
  getOrders: async (params?: Record<string, unknown>): Promise<PaginatedResponse<Order> | Order[]> => {
    const response = await api.get("/orders", { params });
    return response.data;
  },

  getOrder: async (id: string): Promise<Order> => {
    const response = await api.get(`/orders/${id}`);
    return response.data;
  },

  createOrder: async (data: Partial<Order>): Promise<Order> => {
    const response = await api.post("/orders", data);
    return response.data;
  },

  updateOrderStatus: async (id: string, status: string): Promise<Order> => {
    const response = await api.patch(`/orders/${id}/status`, { status });
    return response.data;
  },
};
