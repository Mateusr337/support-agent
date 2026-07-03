import { useNavigate } from "react-router-dom";
import Button from "../../../components/ui/Button";
import { useAuth } from "../../auth/hooks/useAuth";
import "./ChatHeader.css";

export default function ChatHeader() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <header className="chat-header">
      <div className="chat-header-brand">
        <div className="chat-header-logo" aria-hidden="true">
          HP
        </div>
        <div>
          <h1>Support Agent</h1>
          <p>HP document assistant</p>
        </div>
      </div>

      <div className="chat-header-actions">
        {user && <span className="chat-header-user">{user.name}</span>}
        <Button variant="ghost" size="sm" onClick={handleLogout}>
          Sign out
        </Button>
      </div>
    </header>
  );
}
