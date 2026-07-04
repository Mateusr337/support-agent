import { Fragment, useEffect, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { useAuditLogs } from '../hooks/useAuditLogs';
import { AuditLog, GetAuditLogsParams } from '../../../types/api/audit';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Spinner from '../../../components/ui/Spinner';
import './AuditLogList.css';

function auditTypeClass(type: string): string {
  return `type-${type.toLowerCase().replace(/\s+/g, '-')}`;
}

function formatLogDataForDisplay(data: unknown): string {
  return JSON.stringify(data, null, 2).replace(/\\n/g, '\n');
}

export default function AuditLogList() {
  const { logs, loading, loadingMore, hasMore, error, fetchLogs, loadMore } = useAuditLogs();
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  const [filters, setFilters] = useState({
    session_id: '',
    turn_id: '',
  });

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  useEffect(() => {
    if (loadingMore || !hasMore) {
      return;
    }

    const wrapperEl = wrapperRef.current;
    if (!wrapperEl) {
      return;
    }

    function handleScroll() {
      const el = wrapperRef.current;
      if (!el || loadingMore) {
        return;
      }

      const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
      if (distanceFromBottom < 80) {
        void loadMore();
      }
    }

    wrapperEl.addEventListener('scroll', handleScroll, { passive: true });
    return () => wrapperEl.removeEventListener('scroll', handleScroll);
  }, [loadingMore, hasMore, loadMore]);

  useEffect(() => {
    const el = wrapperRef.current;
    if (!el || loading || loadingMore || !hasMore) {
      return;
    }

    if (el.scrollHeight <= el.clientHeight) {
      void loadMore();
    }
  }, [logs, loading, loadingMore, hasMore, loadMore]);

  const handleFilterChange = (e: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFilters((prev) => ({ ...prev, [name]: value }));
  };

  const handleApplyFilters = () => {
    const params: GetAuditLogsParams = {};
    if (filters.session_id) params.session_id = filters.session_id;
    if (filters.turn_id) params.turn_id = filters.turn_id;
    fetchLogs(params);
  };

  const handleClearFilters = () => {
    setFilters({ session_id: '', turn_id: '' });
    fetchLogs();
  };

  const toggleExpand = (id: number) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="audit-log-container">
      <div className="audit-log-header">
        <h2>Audit Logs</h2>
      </div>

      <div className="audit-log-filters">
        <Input
          className="audit-filter-field"
          type="text"
          name="session_id"
          placeholder="Session ID"
          value={filters.session_id}
          onChange={handleFilterChange}
        />
        <Input
          className="audit-filter-field"
          type="text"
          name="turn_id"
          placeholder="Turn ID"
          value={filters.turn_id}
          onChange={handleFilterChange}
        />
        <Button variant="primary" size="sm" onClick={handleApplyFilters}>Apply</Button>
        <Button variant="secondary" size="sm" onClick={handleClearFilters}>Clear</Button>
      </div>

      {error && <div className="audit-log-error">{error}</div>}

      <div ref={wrapperRef} className="audit-log-table-wrapper scrollable">
        {loading ? (
          <div className="audit-log-loading">
            <Spinner />
          </div>
        ) : (
          <table className="audit-log-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Type</th>
                <th>Status</th>
                <th>Message</th>
                <th>User ID</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="audit-log-empty">No logs found.</td>
                </tr>
              ) : (
                logs.map((log: AuditLog) => (
                  <Fragment key={log.id}>
                    <tr className={expandedId === log.id ? 'expanded-row' : ''}>
                      <td>{log.id}</td>
                      <td><span className={`badge ${auditTypeClass(log.type)}`}>{log.type}</span></td>
                      <td><span className={`badge status-${log.status}`}>{log.status}</span></td>
                      <td>{log.message}</td>
                      <td>{log.user_id}</td>
                      <td>{new Date(log.created_at).toLocaleString()}</td>
                      <td>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleExpand(log.id)}
                        >
                          {expandedId === log.id ? 'Hide Data' : 'View Data'}
                        </Button>
                      </td>
                    </tr>
                    {expandedId === log.id && (
                      <tr className="audit-log-data-row">
                        <td colSpan={7}>
                          <div className="audit-log-data-details">
                            <div className="audit-log-metadata">
                              <p><strong>Session ID:</strong> {log.session_id}</p>
                              <p><strong>Turn ID:</strong> {log.turn_id}</p>
                            </div>
                            {log.data ? (
                              <pre className="audit-log-json">
                                {formatLogDataForDisplay(log.data)}
                              </pre>
                            ) : (
                              <p className="audit-log-no-data">No additional data</p>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))
              )}
              {loadingMore && (
                <tr>
                  <td colSpan={7} className="audit-log-loading-more">
                    <Spinner label="Loading more logs" />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
