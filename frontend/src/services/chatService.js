import { apiRequest } from "./api.js";

export const chatService = {
  async listConversations() {
    return apiRequest("/api/v1/chat/conversations");
  },

  async sendMessage(conversationId, content) {
    return apiRequest(`/api/v1/chat/conversations/${conversationId}/messages`, {
      method: "POST",
      body: { content },
    });
  },
};
