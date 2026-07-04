import { useEffect, useRef, useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import Button from "../ui/Button";
import { useAuth } from "../../features/auth/hooks/useAuth";
import "./AppHeader.css";

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

function MenuIcon() {
  return (
    <svg
      className="app-header-menu-icon"
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
    >
      <circle cx="12" cy="5" r="1.75" />
      <circle cx="12" cy="12" r="1.75" />
      <circle cx="12" cy="19" r="1.75" />
    </svg>
  );
}

interface AppHeaderProps {
  onReloadClick?: () => void;
  reloadDisabled?: boolean;
}

export default function AppHeader({ onReloadClick, reloadDisabled = false }: AppHeaderProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  function handleLogout() {
    setMenuOpen(false);
    logout();
    navigate("/login", { replace: true });
  }

  function closeMenu() {
    setMenuOpen(false);
  }

  function handleReloadClick() {
    closeMenu();
    onReloadClick?.();
  }

  useEffect(() => {
    if (!menuOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [menuOpen]);

  return (
    <header className="app-header">
      <NavLink to="/chat" className="app-header-brand">
        <div className="app-header-logo" aria-hidden="true">
          HP
        </div>
        <div>
          <h1>Support Agent</h1>
          <p>HP document assistant</p>
        </div>
      </NavLink>

      <div className="app-header-actions">
        {user && (
          <div className="app-header-user">
            <span className="app-header-avatar" aria-hidden="true">
              {getInitials(user.name)}
            </span>
            <span className="app-header-user-name">{user.name}</span>
          </div>
        )}

        <div className="app-header-menu" ref={menuRef}>
          <Button
            variant="ghost"
            size="sm"
            className="app-header-menu-trigger"
            aria-label="Open menu"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <MenuIcon />
          </Button>

          {menuOpen && (
            <div className="app-header-menu-dropdown" role="menu">
              {onReloadClick && (
                <button
                  type="button"
                  className="app-header-menu-item"
                  role="menuitem"
                  disabled={reloadDisabled}
                  onClick={handleReloadClick}
                >
                  New chat
                </button>
              )}
              <NavLink
                to="/stats"
                className="app-header-menu-item"
                role="menuitem"
                onClick={closeMenu}
              >
                Stats
              </NavLink>
              <NavLink
                to="/audit"
                className="app-header-menu-item"
                role="menuitem"
                onClick={closeMenu}
              >
                Audit
              </NavLink>
              <div className="app-header-menu-divider" role="separator" />
              <button
                type="button"
                className="app-header-menu-item app-header-menu-item-danger"
                role="menuitem"
                onClick={handleLogout}
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
