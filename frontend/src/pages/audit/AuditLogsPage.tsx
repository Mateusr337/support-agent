import AppHeader from '../../components/layout/AppHeader';
import AuditLogList from '../../features/audit/components/AuditLogList';
import './AuditLogsPage.css';

export default function AuditLogsPage() {
  return (
    <div className="audit-logs-page">
      <AppHeader />
      <div className="audit-logs-page-content">
        <AuditLogList />
      </div>
    </div>
  );
}
