import { useState, useCallback, useRef } from 'react';
import { AuditLog, GetAuditLogsParams } from '../../../types/api/audit';
import { auditService, PAGE_SIZE } from '../../../services/auditService';

export function useAuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeParamsRef = useRef<Omit<GetAuditLogsParams, 'offset' | 'limit'>>({});
  const loadingMoreRef = useRef(false);

  const fetchLogs = useCallback(async (params?: GetAuditLogsParams) => {
    setLoading(true);
    setError(null);
    activeParamsRef.current = {
      session_id: params?.session_id,
      turn_id: params?.turn_id,
    };
    try {
      const page = await auditService.getLogs({
        ...activeParamsRef.current,
        limit: PAGE_SIZE,
      });
      setLogs(page.items);
      setHasMore(page.has_more);
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

  const loadMore = useCallback(async () => {
    if (loadingMoreRef.current || !hasMore || logs.length === 0) {
      return;
    }

    loadingMoreRef.current = true;
    const oldestId = logs[logs.length - 1].id;
    setLoadingMore(true);
    setError(null);

    try {
      const page = await auditService.getLogs({
        ...activeParamsRef.current,
        limit: PAGE_SIZE,
        offset: oldestId,
      });
      setHasMore(page.has_more);
      if (page.items.length > 0) {
        setLogs((current) => [...current, ...page.items]);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to load more audit logs');
      }
    } finally {
      loadingMoreRef.current = false;
      setLoadingMore(false);
    }
  }, [hasMore, logs]);

  return {
    logs,
    loading,
    loadingMore,
    hasMore,
    error,
    fetchLogs,
    loadMore,
  };
}
