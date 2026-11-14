import axios from "axios";

export const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const api = axios.create({ baseURL: API, withCredentials: true });

api.interceptors.request.use((config) => {
  config.headers["X-Lang"] = localStorage.getItem("giftaol_lang") || "en";
  return config;
});

export function errMsg(e, fallback = "Something went wrong. Please try again.") {
  const detail = e?.response?.data?.detail;
  if (detail == null) {
    const lang = localStorage.getItem("giftaol_lang");
    return lang === "fr" ? "Un problème est survenu. Veuillez réessayer dans quelques minutes." : "Something went wrong. Please try again in a few minutes.";
  }
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d?.msg || JSON.stringify(d)).join(" ");
  if (typeof detail.message === "string") return detail.message;
  if (typeof detail.msg === "string") return detail.msg;
  return fallback;
}

export const fmtMoney = (n, lang = "en") =>
  new Intl.NumberFormat(lang === "fr" ? "fr-CA" : "en-CA", { style: "currency", currency: "CAD" }).format(n || 0);

export const fmtDate = (iso, lang = "en") =>
  iso ? new Date(iso).toLocaleDateString(lang === "fr" ? "fr-CA" : "en-CA", { year: "numeric", month: "short", day: "numeric" }) : "";

export const fmtDateTime = (iso, lang = "en") =>
  iso ? new Date(iso).toLocaleString(lang === "fr" ? "fr-CA" : "en-CA") : "";

export const formatCode = (c = "") => c.match(/.{1,4}/g)?.join("-") || "";
