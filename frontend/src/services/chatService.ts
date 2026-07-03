import type {
  ChatMessageResponse,
  ChatMessagesPageResponse,
  ChatSessionResponse,
  SendMessageApiResponse,
} from "../types/api/chat";
import type { ChatMessage, SendMessageResult } from "../types/chat";
import { apiRequest } from "./api";

export const PAGE_SIZE = 10;

function mapMessage(apiMessage: ChatMessageResponse): ChatMessage {
  return {
    id: String(apiMessage.id),
    role: apiMessage.role === "user" ? "user" : "assistant",
    content: apiMessage.content,
    createdAt: apiMessage.created_at,
  };
}

export interface GetSessionMessagesOptions {
  limit?: number;
  offset?: number;
}

export const chatService = {
  async getOrCreateActiveSession(): Promise<ChatSessionResponse> {
    return apiRequest<ChatSessionResponse>("/api/v1/chat/conversations/active");
  },

  async getSessionMessages(
    sessionId: string,
    { limit = PAGE_SIZE, offset }: GetSessionMessagesOptions = {}
  ): Promise<ChatMessagesPageResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (offset !== undefined && offset !== null) {
      params.set("offset", String(offset));
    }

    return apiRequest<ChatMessagesPageResponse>(
      `/api/v1/chat/conversations/${sessionId}/messages?${params}`
    );
  },

  async sendMessage(sessionId: string, content: string): Promise<SendMessageResult> {
    const result = await apiRequest<SendMessageApiResponse>(
      `/api/v1/chat/conversations/${sessionId}/messages`,
      {
        method: "POST",
        body: { content },
      }
    );

    return {
      user_message: mapMessage(result.user_message),
      assistant_message: mapMessage(result.assistant_message),
    };
  },

  mapMessage,

  mapMessages(apiMessages: ChatMessageResponse[]): ChatMessage[] {
    return apiMessages.map(mapMessage);
  },
};
