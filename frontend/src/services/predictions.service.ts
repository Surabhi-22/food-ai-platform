import { api } from "@/lib/api";
import { Prediction } from "@/types/api";

export const PredictionsService = {
  // GET /api/v1/analytics/revenue
  getAnalytics: async (): Promise<Record<string, unknown>> => {
    const response = await api.get("/analytics/revenue");
    return response.data;
  },

  // GET /api/v1/forecasts/summary
  getPredictions: async (): Promise<Record<string, unknown>> => {
    const response = await api.get("/forecasts/summary");
    return response.data;
  },
};
