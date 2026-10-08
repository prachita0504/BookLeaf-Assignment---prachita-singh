// Holds the logged-in user (from GET /auth/me) and exposes login / register / logout.
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as authApi from "../api/auth";
import { AUTH_CHANGED_EVENT } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [checking, setChecking] = useState(true); // true until we know whether a session exists

  useEffect(() => {
    authApi
      .me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  // Re-check the session when a request is rejected or the tab regains focus: if another tab logged
  // in as someone else (or logged out), this tab follows instead of showing stale or broken pages.
  useEffect(() => {
    const recheck = () =>
      authApi
        .me()
        .then((u) => setUser((prev) => (prev?.id === u.id ? prev : u)))
        .catch(() => setUser(null));
    const onVisible = () => document.visibilityState === "visible" && recheck();
    window.addEventListener(AUTH_CHANGED_EVENT, recheck);
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, recheck);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  const login = useCallback(async (email, password) => {
    const u = await authApi.login(email, password);
    setUser(u);
    return u;
  }, []);

  const register = useCallback(async (data) => {
    const u = await authApi.register(data);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout().catch(() => {});
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, checking, login, register, logout }), [user, checking, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);

/** Where each role lands after logging in. */
export const homeFor = (user) => (user?.role === "ADMIN" ? "/admin" : "/books");
