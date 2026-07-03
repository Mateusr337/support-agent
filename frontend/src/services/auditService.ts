import { apiRequest } from './api';
import { AuditLog, GetAuditLogsParams } from '../types/api/audit';

export const auditService = {
  getLogs: async (params?: GetAuditLogsParams): Promise<AuditLog[]> => {
    let query = '';
    if (params) {
      const searchParams = new URLSearchParams();
      if (params.session_id) searchParams.append('session_id', params.session_id);
      if (params.turn_id) searchParams.append('turn_id', params.turn_id);
      const queryString = searchParams.toString();
      if (queryString) {
        query = `?${queryString}`;
      }
    }
    return apiRequest<AuditLog[]>(`/api/v1/audit/logs${query}`);
  },
};
