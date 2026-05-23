"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

interface AuthContextValue {
  authenticated: boolean;
  loading: boolean;
  displayName: string | null;
  login: (identifier: string, password: string) => Promise<string | null>;
  signup: (identifier: string, identifierType: "email" | "phone", displayName: string, password: string) => Promise<string | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  authenticated: false,
  loading: true,
  displayName: null,
  login: async () => "Not initialized",
  signup: async () => "Not initialized",
  logout: () => {},
});

const TOKEN_KEY = "autoreg-auth-token";
const NAME_KEY = "autoreg-display-name";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [displayName, setDisplayName] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      setLoading(false);
      return;
    }
    fetch("/api/auth", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    })
      .then((r) => {
        if (r.ok) {
          setAuthenticated(true);
          setDisplayName(localStorage.getItem(NAME_KEY));
        } else {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(NAME_KEY);
        }
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(NAME_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (identifier: string, password: string): Promise<string | null> => {
    try {
      const res = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, password }),
      });
      const data = await res.json();
      if (data.ok && data.token) {
        localStorage.setItem(TOKEN_KEY, data.token);
        localStorage.setItem(NAME_KEY, data.displayName || "User");
        setDisplayName(data.displayName || "User");
        setAuthenticated(true);
        return null;
      }
      return data.error || "Invalid credentials";
    } catch {
      return "Connection failed";
    }
  }, []);

  const signup = useCallback(async (
    identifier: string,
    identifierType: "email" | "phone",
    name: string,
    password: string,
  ): Promise<string | null> => {
    try {
      const res = await fetch("/api/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ identifier, identifierType, displayName: name, password }),
      });
      const data = await res.json();
      if (data.ok && data.token) {
        localStorage.setItem(TOKEN_KEY, data.token);
        localStorage.setItem(NAME_KEY, data.displayName || name);
        setDisplayName(data.displayName || name);
        setAuthenticated(true);
        return null;
      }
      return data.error || "Sign up failed";
    } catch {
      return "Connection failed";
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(NAME_KEY);
    setDisplayName(null);
    setAuthenticated(false);
  }, []);

  return (
    <AuthContext.Provider value={{ authenticated, loading, displayName, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
