import { useCallback } from "react";
import axios from "axios";
import { useAuth } from "@clerk/react";

// Same-origin on purpose: the backend picks the city from the host the visitor used.
export const api = axios.create({ baseURL: "/api" });

export function useAuthedApi() {
  const { getToken } = useAuth();
  return useCallback(
    async (config) => {
      const token = await getToken();
      return api.request({ ...config, headers: { ...(config.headers || {}), Authorization: `Bearer ${token}` } });
    },
    [getToken],
  );
}

export const errorText = (err) => err?.response?.data?.detail || err?.message || "Something went wrong";
