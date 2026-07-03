import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { AuthContextValue, User } from "../../../types/auth";
import { authService } from "../../../services/authService";
import { getToken } from "../../../lib/authStorage";

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }

    authService
      .getMe()
      .then(setUser)
      .catch(() => {
        authService.logout();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const authenticatedUser = await authService.login(email, password);
    setUser(authenticatedUser);
    return authenticatedUser;
  }, []);

  const register = useCallback(async (email: string, name: string, password: string) => {
    await authService.register(email, name, password);
    const authenticatedUser = await authService.login(email, password);
    setUser(authenticatedUser);
    return authenticatedUser;
  }, []);

  const logout = useCallback(() => {
    authService.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      register,
      logout,
    }),
    [user, loading, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
