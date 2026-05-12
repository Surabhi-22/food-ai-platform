import { api } from "@/lib/api";
import { MenuItem, PaginatedResponse } from "@/types/api";

export const MenuService = {
  getMenuItems: async (params?: Record<string, unknown>): Promise<PaginatedResponse<MenuItem> | MenuItem[]> => {
    const response = await api.get("/menu", { params });
    return response.data;
  },

  getMenuItem: async (id: string): Promise<MenuItem> => {
    const response = await api.get(`/menu/${id}`);
    return response.data;
  },

  createMenuItem: async (data: Partial<MenuItem>): Promise<MenuItem> => {
    const response = await api.post("/menu", data);
    return response.data;
  },

  updateMenuItem: async (id: string, data: Partial<MenuItem>): Promise<MenuItem> => {
    const response = await api.put(`/menu/${id}`, data);
    return response.data;
  },

  deleteMenuItem: async (id: string): Promise<void> => {
    await api.delete(`/menu/${id}`);
  },
};
