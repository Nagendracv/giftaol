import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { api } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // Captured on first render, before AuthCallback clears the URL hash.
  const fromOAuth = useRef(window.location.hash.includes("session_id="));

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/auth/me");
      setUser(data || false);
    } catch {
      setUser(false);
    }
  }, []);

  useEffect(() => {
    // Returning from Google: AuthCallback exchanges the session and sets the user.
    if (fromOAuth.current) return;
    refresh();
  }, [refresh]);

  const logout = useCallback(async () => {
    await api.post("/auth/logout").catch(() => {});
    setUser(false);
  }, []);

  return <AuthCtx.Provider value={{ user, setUser, refresh, logout }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
