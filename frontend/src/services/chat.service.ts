import { api } from "@/lib/api";

export interface ChatResponse {
  session_id: string;
  reply: string;
  sources: string[];
  source_chunks?: any[];
}

export const ChatService = {
  sendMessage: async (message: string, sessionId?: string | null): Promise<ChatResponse> => {
    // The backend endpoint is /chat, not /chatbot
    // The payload expects { message, session_id }
    const response = await api.post("/chat", { 
      message, 
      session_id: sessionId || undefined 
    });
    return response.data;
  },

  getHistory: async (sessionId?: string | null) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const response = await api.get("/chat/history", { params });
    return response.data;
  },

  getSessions: async () => {
    const response = await api.get("/chat/sessions");
    return response.data;
  },

  clearHistory: async (sessionId?: string | null) => {
    const params = sessionId ? { session_id: sessionId } : {};
    const response = await api.delete("/chat/history", { params });
    return response.data;
  }
};
