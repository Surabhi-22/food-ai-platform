import { api, nextApi } from "@/lib/api";
import { User } from "@/types/api";
import axios from "axios";

export const AuthService = {
  login: async (credentials: Record<string, string>): Promise<{ access_token: string; user: User }> => {
    // Calls Next.js API route to set HttpOnly cookies
    const response = await nextApi.post("/auth/login", credentials);
    const data = response.data;
    // Store tokens in localStorage so api.ts can attach them to direct FastAPI calls
    if (data?.access_token) {
      localStorage.setItem("access_token", data.access_token);
    }
    if (data?.refresh_token) {
      localStorage.setItem("refresh_token", data.refresh_token);
    }
    return data;
  },

  register: async (userData: Record<string, unknown>): Promise<User> => {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    // Hits FastAPI directly
    const response = await axios.post(`${backendUrl}/auth/register`, userData);

    // Auto login to set HttpOnly cookies and store tokens
    const loginRes = await nextApi.post("/auth/login", {
      email: userData.email,
      password: userData.password,
    });
    if (loginRes.data?.access_token) {
      localStorage.setItem("access_token", loginRes.data.access_token);
    }
    if (loginRes.data?.refresh_token) {
      localStorage.setItem("refresh_token", loginRes.data.refresh_token);
    }

    return response.data;
  },

  logout: async (): Promise<void> => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    await nextApi.post("/auth/logout");
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await api.get("/auth/me");
    return response.data;
  },
};
