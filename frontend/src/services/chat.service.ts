import { api } from "@/lib/api";

export const ChatService = {
  sendMessage: async (question: string) => {
    const response = await api.post("/chatbot", { question });
    return response.data;
  },
};
