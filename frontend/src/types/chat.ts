export type MessageRole = "user" | "assistant";

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  createdAt: string;
}

export type ChatStreamEvent =
  | { type: "turn_started"; turn_id: string }
  | { type: "tool_call"; name: string }
  | { type: "token"; content: string }
  | { type: "done"; assistant_message_id: number; content: string }
  | { type: "error"; message: string };

export interface StreamingState {
  turnId: string;
  tool: string | null;
  content: string;
}

export interface UseChatReturn {
  messages: ChatMessage[];
  loading: boolean;
  loadingOlder: boolean;
  hasMoreOlder: boolean;
  sending: boolean;
  streaming: StreamingState | null;
  reloadingSession: boolean;
  error: string;
  sendMessage: (content: string) => Promise<void>;
  loadOlderMessages: () => Promise<void>;
  reloadSession: () => Promise<boolean>;
  canSend: boolean;
}
