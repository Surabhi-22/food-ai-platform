import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { toast } from "sonner";

// ── Base Instances ──────────────────────────────────────────────────────────

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
  timeout: 30000,
});

export const nextApi = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// ── Request Interceptor — attach Bearer token ───────────────────────────────

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// ── Token Refresh State ─────────────────────────────────────────────────────

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (err: unknown) => void;
}> = [];

function processQueue(error: unknown, token: string | null) {
  failedQueue.forEach((prom) => {
    if (error) prom.reject(error);
    else prom.resolve(token!);
  });
  failedQueue = [];
}

// ── Response Interceptor ────────────────────────────────────────────────────

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // 401 Unauthorized → try to refresh token
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve, reject) => {
          failedQueue.push({
            resolve: (token: string) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              resolve(api(originalRequest));
            },
            reject: (err) => reject(err),
          });
        });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        const res = await nextApi.post("/auth/refresh");
        const newToken = res.data?.access_token;

        if (newToken) {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          processQueue(null, newToken);
          return api(originalRequest);
        }
      } catch (refreshError) {
        processQueue(refreshError, null);
        // Redirect to login
        if (typeof window !== "undefined") {
          toast.error("Session expired. Please log in again.");
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    // 403 Forbidden → redirect to dashboard with message
    if (error.response?.status === 403) {
      toast.error("Access denied. You don't have permission for this action.");
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/dashboard")) {
        window.location.href = "/dashboard";
      }
    }

    // 422 Validation Error → extract field errors
    if (error.response?.status === 422) {
      const data = error.response.data as { detail?: Array<{ loc: string[]; msg: string; type: string }> };
      const errors = data?.detail;
      if (Array.isArray(errors)) {
        errors.forEach((e) => {
          const field = e.loc[e.loc.length - 1];
          toast.error(`${field}: ${e.msg}`);
        });
      } else {
        toast.error("Validation error. Please check your input.");
      }
    }

    // 429 Rate Limited
    if (error.response?.status === 429) {
      toast.error("Too many requests. Please wait a moment and try again.");
    }

    // 500+ Server Error
    if (error.response && error.response.status >= 500) {
      toast.error("Server error. Our team has been notified. Please try again later.");
    }

    // Network Error (no response at all)
    if (!error.response && error.message === "Network Error") {
      toast.error("Network error. Please check your internet connection.");
    }

    return Promise.reject(error);
  }
);
