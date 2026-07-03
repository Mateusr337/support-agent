import { apiRequest } from "./api.js";

export const PAGE_SIZE = 10;

function mapMessage(apiMessage) {
  return {
    id: String(apiMessage.id),
    role: apiMessage.role,
    content: apiMessage.content,
    createdAt: apiMessage.created_at,
  };
}

export const chatService = {
  async getOrCreateActiveSession() {
    return apiRequest("/api/v1/chat/conversations/active");
  },

  async getSessionMessages(sessionId, { limit = PAGE_SIZE, offset } = {}) {
    const params = new URLSearchParams({ limit: String(limit) });
    if (offset !== undefined && offset !== null) {
      params.set("offset", String(offset));
    }

    return apiRequest(`/api/v1/chat/conversations/${sessionId}/messages?${params}`);
  },

  async sendMessage(sessionId, content) {
    const result = await apiRequest(`/api/v1/chat/conversations/${sessionId}/messages`, {
      method: "POST",
      body: { content },
    });

    return {
      user_message: mapMessage(result.user_message),
      assistant_message: mapMessage(result.assistant_message),
    };
  },

  mapMessage,

  mapMessages(apiMessages) {
    return apiMessages.map(mapMessage);
  },
};
