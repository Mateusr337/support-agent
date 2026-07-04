import type { ChatMessageResponse, ChatMessagesPageResponse, ChatSessionResponse } from "../types/api/chat";
import type { ChatMessage, ChatStreamEvent } from "../types/chat";
import { API_URL } from "../lib/env";
import { getToken } from "../lib/authStorage";
import { ApiError } from "./api";

export const PAGE_SIZE = 20;

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

function parseSseBlock(block: string): ChatStreamEvent | null {
  const dataLine = block
    .split("\n")
    .find((line) => line.startsWith("data: "));

  if (!dataLine) {
    return null;
  }

  return JSON.parse(dataLine.slice(6)) as ChatStreamEvent;
}

export const chatService = {
  async getOrCreateActiveSession(): Promise<ChatSessionResponse> {
    const token = getToken();
    const response = await fetch(`${API_URL}/api/v1/chat/conversations/active`, {
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, response.statusText);
    }

    return response.json() as Promise<ChatSessionResponse>;
  },

  async getSessionMessages(
    sessionId: string,
    { limit = PAGE_SIZE, offset }: GetSessionMessagesOptions = {},
  ): Promise<ChatMessagesPageResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (offset !== undefined && offset !== null) {
      params.set("offset", String(offset));
    }

    const token = getToken();
    const response = await fetch(
      `${API_URL}/api/v1/chat/conversations/${sessionId}/messages?${params}`,
      {
        headers: {
          Accept: "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      },
    );

    if (!response.ok) {
      throw new ApiError(response.status, response.statusText);
    }

    return response.json() as Promise<ChatMessagesPageResponse>;
  },

  async sendMessageStream(
    sessionId: string,
    content: string,
    onEvent: (event: ChatStreamEvent) => void,
  ): Promise<void> {
    const token = getToken();
    const response = await fetch(
      `${API_URL}/api/v1/chat/conversations/${sessionId}/messages`,
      {
        method: "POST",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ content }),
      },
    );

    if (!response.ok) {
      let detail: string | undefined;
      const contentType = response.headers.get("content-type") ?? "";
      if (contentType.includes("application/json")) {
        const payload = (await response.json()) as { detail?: string };
        detail = typeof payload.detail === "string" ? payload.detail : undefined;
      }
      throw new ApiError(response.status, detail ?? response.statusText, detail);
    }

    const reader = response.body?.getReader();
    if (!reader) {
      throw new ApiError(500, "Streaming response body is unavailable");
    }

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        const event = parseSseBlock(block);
        if (event) {
          onEvent(event);
        }
      }
    }

    if (buffer.trim()) {
      const event = parseSseBlock(buffer);
      if (event) {
        onEvent(event);
      }
    }
  },

  async reloadSession(): Promise<ChatSessionResponse> {
    const token = getToken();
    const response = await fetch(`${API_URL}/api/v1/chat/conversations/reload`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      throw new ApiError(response.status, response.statusText);
    }

    return response.json() as Promise<ChatSessionResponse>;
  },

  mapMessages(apiMessages: ChatMessageResponse[]): ChatMessage[] {
    return apiMessages.map(mapMessage);
  },
};
