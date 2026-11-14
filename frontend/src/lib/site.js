import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

const SiteCtx = createContext(null);

export function SiteProvider({ children }) {
  const [config, setConfig] = useState(null);
  const [content, setContent] = useState(null);

  const reload = async () => {
    const [c, l] = await Promise.all([api.get("/public/config"), api.get("/content")]);
    setConfig(c.data);
    setContent(l.data);
  };

  useEffect(() => {
    reload().catch(() => {});
  }, []);

  return <SiteCtx.Provider value={{ config, content, reload }}>{children}</SiteCtx.Provider>;
}

export const useSite = () => useContext(SiteCtx);
