import { useState, useCallback } from 'react';
import { AuditLog, GetAuditLogsParams } from '../../../types/api/audit';
import { auditService } from '../../../services/auditService';

export function useAuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLogs = useCallback(async (params?: GetAuditLogsParams) => {
    setLoading(true);
    setError(null);
    try {
      const data = await auditService.getLogs(params);
      setLogs(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch audit logs');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    logs,
    loading,
    error,
    fetchLogs,
  };
}
