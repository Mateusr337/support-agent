export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

export interface SendMessageResult {
  user_message: ChatMessage;
  assistant_message: ChatMessage;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  loading: boolean;
  loadingOlder: boolean;
  hasMoreOlder: boolean;
  sending: boolean;
  error: string;
  sendMessage: (content: string) => Promise<void>;
  loadOlderMessages: () => Promise<void>;
  canSend: boolean;
}
