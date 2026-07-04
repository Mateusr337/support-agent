export interface ChatSessionResponse {
  id: string;
  user_id: number;
  created_at: string;
  updated_at: string;
  finalized_at: string | null;
}

export interface ChatMessageResponse {
  id: number;
  chat_session_id: string;
  user_id: number;
  role: string;
  content: string;
  created_at: string;
}

export interface ChatMessagesPageResponse {
  items: ChatMessageResponse[];
  has_more: boolean;
}

export interface SendMessageRequest {
  content: string;
}
