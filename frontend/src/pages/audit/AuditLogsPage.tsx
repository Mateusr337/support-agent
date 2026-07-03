import { useNavigate } from 'react-router-dom';
import AuditLogList from '../../features/audit/components/AuditLogList';
import Button from '../../components/ui/Button';

export default function AuditLogsPage() {
  const navigate = useNavigate();

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
      <header style={{ padding: '0.875rem 1.5rem', borderBottom: '1px solid var(--color-border)', display: 'flex', alignItems: 'center', gap: '1rem', background: 'var(--color-bg-elevated)' }}>
        <Button variant="ghost" size="sm" onClick={() => navigate('/chat')}>
          ← Back to Chat
        </Button>
      </header>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <AuditLogList />
      </div>
    </div>
  );
}
