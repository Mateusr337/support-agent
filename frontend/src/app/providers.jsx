import { AuthProvider, useAuth } from "../features/auth/hooks/useAuth.jsx";

export default function Providers({ children }) {
  return <AuthProvider>{children}</AuthProvider>;
}

export { useAuth };
