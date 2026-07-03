import { Fragment, useEffect, useState } from 'react';
import type { ChangeEvent } from 'react';
import { useAuditLogs } from '../hooks/useAuditLogs';
import { AuditLog, GetAuditLogsParams } from '../../../types/api/audit';
import Button from '../../../components/ui/Button';
import Input from '../../../components/ui/Input';
import Spinner from '../../../components/ui/Spinner';
import './AuditLogList.css';

export default function AuditLogList() {
  const { logs, loading, error, fetchLogs } = useAuditLogs();
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const [filters, setFilters] = useState({
    session_id: '',
    turn_id: '',
  });

  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

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

      <div className="audit-log-table-wrapper">
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
                      <td><span className={`badge type-${log.type}`}>{log.type}</span></td>
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
                                {JSON.stringify(log.data, null, 2)}
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
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
