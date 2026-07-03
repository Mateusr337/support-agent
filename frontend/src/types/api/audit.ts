export interface AuditLog {
  id: number;
  session_id: string;
  user_id: number;
  turn_id: string;
  type: string;
  status: string;
  message: string;
  data: Record<string, unknown> | null;
  created_at: string;
}

export interface AuditLogsPageResponse {
  items: AuditLog[];
  has_more: boolean;
}

export interface GetAuditLogsParams {
  session_id?: string;
  turn_id?: string;
  limit?: number;
  offset?: number;
}
