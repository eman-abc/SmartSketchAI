import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';
import { getAccessToken } from '../lib/authStore';
import {
  loginWithToken,
  registerUser,
} from '../lib/api';
import { setTokens, clearTokens } from '../lib/authStore';

type AuthContextValue = {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [accessToken, setAccessToken] = useState<string | null>(() =>
    getAccessToken()
  );

  const login = useCallback(
    async (username: string, password: string) => {
      const { access, refresh } = await loginWithToken(username, password);
      setTokens(access, refresh);
      setAccessToken(access);
      navigate('/', { replace: true });
    },
    [navigate]
  );

  const register = useCallback(
    async (username: string, email: string, password: string) => {
      await registerUser({ username, email, password, role: 'general' });
      navigate('/login', { replace: true });
    },
    [navigate]
  );

  const logout = useCallback(() => {
    clearTokens();
    setAccessToken(null);
    navigate('/login', { replace: true });
  }, [navigate]);

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated: !!accessToken,
      login,
      register,
      logout,
    }),
    [accessToken, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
