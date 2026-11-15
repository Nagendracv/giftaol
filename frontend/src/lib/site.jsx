import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { api } from "@/lib/api";

const SiteContext = createContext(null);

export function SiteProvider({ children }) {
  const [site, setSite] = useState(null);
  const location = useLocation();
  const tracked = useRef(null);

  const load = useCallback(async () => {
    const { data } = await api.get("/site");
    document.documentElement.lang = data.locale;
    setSite(data);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (tracked.current === location.pathname) return; // StrictMode runs effects twice in development
    tracked.current = location.pathname;
    api.post("/track", { path: location.pathname }).catch(() => {});
  }, [location.pathname]);

  const setLocale = async (locale) => {
    document.cookie = `lang=${locale}; path=/; max-age=31536000; samesite=lax`;
    await load();
  };

  const t = (key) => site?.texts?.[key] ?? key;
  if (!site) return null;
  return <SiteContext.Provider value={{ site, t, setLocale }}>{children}</SiteContext.Provider>;
}

export const useSite = () => useContext(SiteContext);
