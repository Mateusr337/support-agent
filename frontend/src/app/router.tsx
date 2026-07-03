import { Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";
import Spinner from "../components/ui/Spinner";
import { useAuth } from "../features/auth/hooks/useAuth";
import ChatPage from "../pages/chat/ChatPage";
import LoginPage from "../pages/login/LoginPage";
import RegisterPage from "../pages/register/RegisterPage";

interface RouteGuardProps {
  children: ReactNode;
}

function ProtectedRoute({ children }: RouteGuardProps) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <Spinner fullPage />;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function GuestRoute({ children }: RouteGuardProps) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <Spinner fullPage />;
  }

  if (isAuthenticated) {
    return <Navigate to="/chat" replace />;
  }

  return children;
}

function RootRedirect() {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return <Spinner fullPage />;
  }

  return <Navigate to={isAuthenticated ? "/chat" : "/login"} replace />;
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route
        path="/login"
        element={
          <GuestRoute>
            <LoginPage />
          </GuestRoute>
        }
      />
      <Route
        path="/register"
        element={
          <GuestRoute>
            <RegisterPage />
          </GuestRoute>
        }
      />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <ChatPage />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
