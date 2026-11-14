import { useEffect, useRef } from "react";
import { useLang } from "../lib/i18n";

const SITE_KEY = process.env.REACT_APP_TURNSTILE_SITE_KEY;

export const Turnstile = ({ onToken, resetKey, testId = "auth-turnstile-container" }) => {
  const ref = useRef(null);
  const widgetId = useRef(null);
  const { lang, t } = useLang();

  useEffect(() => {
    let cancelled = false;
    const timer = setInterval(() => {
      if (cancelled || !window.turnstile || !ref.current) return;
      clearInterval(timer);
      if (widgetId.current !== null) {
        window.turnstile.remove(widgetId.current);
      }
      widgetId.current = window.turnstile.render(ref.current, {
        sitekey: SITE_KEY,
        language: lang,
        callback: (tok) => onToken(tok),
        "expired-callback": () => onToken(""),
        "error-callback": () => onToken(""),
      });
    }, 100);
    return () => {
      cancelled = true;
      clearInterval(timer);
      if (widgetId.current !== null && window.turnstile) {
        window.turnstile.remove(widgetId.current);
        widgetId.current = null;
      }
    };
  }, [resetKey, lang]); // eslint-disable-line react-hooks/exhaustive-deps

  return <div ref={ref} data-testid={testId} aria-label={t("turnstile.label")} className="min-h-[65px]" />;
};
