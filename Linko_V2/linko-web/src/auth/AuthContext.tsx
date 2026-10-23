import { createContext, useCallback, useContext, useMemo, useState, useEffect, type ReactNode } from 'react';
import type { AuthUser, Role } from './types';
import { PERMS, ROLE_LABEL } from './types';
import { clearAuth, loadAuth, saveAuth } from './storage';
import { api, invalidateApiCache } from '../api/client';

type AuthCtx = {
  user: AuthUser | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  role: Role | null;
  roleLabel: string;
  can: typeof PERMS;
};

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => loadAuth());

  const login = useCallback(async (username: string, password: string) => {
    const res = await api.login(username, password);
    const u: AuthUser = {
      username: res.username,
      full_name: res.full_name,
      role: res.role as Role,
      token: res.token,
      expires_at: Date.now() + res.expires_in * 1000,
    };
    invalidateApiCache();
    saveAuth(u);
    setUser(u);
  }, []);

  const logout = useCallback(() => {
    // Thu hồi phiên trên server khi có mạng, vẫn đăng xuất cục bộ nếu offline.
    void api.logout().catch(() => undefined);
    invalidateApiCache();
    clearAuth();
    setUser(null);
  }, []);

  useEffect(() => {
    const handleExpired = () => {
      invalidateApiCache();
      clearAuth();
      setUser(null);
    };
    window.addEventListener('linko:auth-expired', handleExpired);
    return () => window.removeEventListener('linko:auth-expired', handleExpired);
  }, []);

  // Check server-side token lifetime after reloading the tab.
  useEffect(() => {
    if (!user) return;
    void api.me().catch(() => {
      // 401 is handled above; keep the screen accessible when merely offline.
    });
  }, [user?.token]);

  const value = useMemo<AuthCtx>(
    () => ({
      user,
      login,
      logout,
      role: user?.role ?? null,
      roleLabel: user ? ROLE_LABEL[user.role] : '',
      can: PERMS,
    }),
    [user, login, logout]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const v = useContext(Ctx);
  if (!v) throw new Error('useAuth outside AuthProvider');
  return v;
}
