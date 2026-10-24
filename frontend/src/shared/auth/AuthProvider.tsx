import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { useApi } from "@/shared/api/ApiProvider";

export type AuthUser = {
  id: string;
  email: string;
  full_name: string;
  role: "owner" | "staff";
  preferred_language: "en" | "ar";
};

type LoginCredentials = {
  email: string;
  password: string;
};

type AuthContextValue = {
  user: AuthUser | null;
  status: "loading" | "authenticated" | "anonymous";
  login: (credentials: LoginCredentials) => Promise<void>;
  logout: () => Promise<void>;
};

type TokenResponse = {
  access: string;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const api = useApi();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthContextValue["status"]>("loading");

  const clearSession = useCallback(() => {
    api.setAccessToken(null);
    setUser(null);
    setStatus("anonymous");
  }, [api]);

  useEffect(() => {
    let active = true;

    async function restoreSession() {
      try {
        const token = await api.post<TokenResponse>("/auth/refresh/", {});
        if (!active) {
          return;
        }
        api.setAccessToken(token.access);
        const currentUser = await api.get<AuthUser>("/auth/me/");
        if (!active) {
          return;
        }
        setUser(currentUser);
        setStatus("authenticated");
      } catch {
        if (active) {
          clearSession();
        }
      }
    }

    void restoreSession();

    return () => {
      active = false;
    };
  }, [api, clearSession]);

  const login = useCallback(
    async (credentials: LoginCredentials) => {
      const token = await api.post<TokenResponse>("/auth/token/", credentials, {
        token: null,
      });
      api.setAccessToken(token.access);
      const currentUser = await api.get<AuthUser>("/auth/me/");
      setUser(currentUser);
      setStatus("authenticated");
    },
    [api],
  );

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout/");
    } finally {
      clearSession();
    }
  }, [api, clearSession]);

  const value = useMemo(() => ({ user, status, login, logout }), [user, status, login, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
