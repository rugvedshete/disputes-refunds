import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, loadSession, saveSession } from "./api";
import type { Session } from "./types";

interface AuthCtx {
  session: Session | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}
const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(loadSession());

  const logout = useCallback(() => { saveSession(null); setSession(null); }, []);
  const login = useCallback(async (email: string, password: string) => {
    const s = await api.login(email, password);
    saveSession(s);
    setSession(s);
  }, []);

  useEffect(() => {
    window.addEventListener("auth:expired", logout);
    return () => window.removeEventListener("auth:expired", logout);
  }, [logout]);

  return <Ctx.Provider value={{ session, login, logout }}>{children}</Ctx.Provider>;
}
