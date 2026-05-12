import { api, nextApi } from "@/lib/api";
import { User } from "@/types/api";
import axios from "axios";

export const AuthService = {
  login: async (credentials: Record<string, string>): Promise<{ access_token: string; user: User }> => {
    // Calls Next.js API route to set HttpOnly cookie
    const response = await nextApi.post("/auth/login", credentials);
    // Store token in localStorage so api.ts can attach it to direct FastAPI calls
    if (response.data?.access_token) {
      localStorage.setItem("access_token", response.data.access_token);
    }
    return response.data;
  },

  register: async (userData: Record<string, unknown>): Promise<User> => {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    // Hits FastAPI directly
    const response = await axios.post(`${backendUrl}/auth/register`, userData);
    
    // Auto login to set HttpOnly cookie
    const loginRes = await nextApi.post("/auth/login", {
      email: userData.email,
      password: userData.password,
    });
    if (loginRes.data?.access_token) {
      localStorage.setItem("access_token", loginRes.data.access_token);
    }

    return response.data;
  },

  logout: async (): Promise<void> => {
    localStorage.removeItem("access_token");
    await nextApi.post("/auth/logout");
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get("/auth/me");
    return response.data;
  },
};
