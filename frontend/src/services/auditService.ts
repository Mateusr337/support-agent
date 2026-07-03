import { apiRequest } from './api';
import { AuditLogsPageResponse, GetAuditLogsParams } from '../types/api/audit';

export const PAGE_SIZE = 25;

export const auditService = {
  getLogs: async (params?: GetAuditLogsParams): Promise<AuditLogsPageResponse> => {
    const searchParams = new URLSearchParams({
      limit: String(params?.limit ?? PAGE_SIZE),
    });
    if (params?.offset !== undefined && params.offset !== null) {
      searchParams.set('offset', String(params.offset));
    }
    if (params?.session_id) {
      searchParams.append('session_id', params.session_id);
    }
    if (params?.turn_id) {
      searchParams.append('turn_id', params.turn_id);
    }
    return apiRequest<AuditLogsPageResponse>(`/api/v1/audit/logs?${searchParams}`);
  },
};
