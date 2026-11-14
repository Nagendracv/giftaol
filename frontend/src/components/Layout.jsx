import { useEffect, useRef } from "react";
import { Link, Outlet, useLocation } from "react-router-dom";
import { Header } from "./Header";
import { useLang } from "../lib/i18n";
import { useSite } from "../lib/site";
import { api } from "../lib/api";

const Footer = () => {
  const { t, lang } = useLang();
  const { content } = useSite();
  const c = content?.[lang];
  return (
    <footer className="border-t border-stone-200 bg-[#F3EDE3] mt-16" data-testid="site-footer">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-10 flex flex-col md:flex-row gap-6 md:items-center md:justify-between">
        <div className="max-w-md">
          <p className="font-serif text-xl text-[#2A4736]">giftaol.ca</p>
          <p className="text-sm text-stone-600 mt-1" data-testid="footer-text">{c?.footer_text}</p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm" aria-label="Footer">
          <Link to="/privacy" className="text-stone-700 hover:text-[#C24C29] underline-offset-4 hover:underline" data-testid="footer-privacy-link">{t("footer.privacy")}</Link>
          <Link to="/terms" className="text-stone-700 hover:text-[#C24C29] underline-offset-4 hover:underline" data-testid="footer-terms-link">{t("footer.terms")}</Link>
          {c?.contact_email && (
            <a href={`mailto:${c.contact_email}`} className="text-stone-700 hover:text-[#C24C29] underline-offset-4 hover:underline" data-testid="footer-contact-link">
              {t("footer.contact")}: {c.contact_email}
            </a>
          )}
        </nav>
      </div>
    </footer>
  );
};

const useTracking = () => {
  const location = useLocation();
  const prev = useRef(null);
  useEffect(() => {
    const path = location.pathname + location.search;
    if (prev.current === path) return;
    const referrer = prev.current ? window.location.origin + prev.current : document.referrer;
    prev.current = path;
    api.post("/track", { path, referrer }).catch(() => {});
  }, [location.pathname, location.search]);
};

export default function Layout() {
  useTracking();
  return (
    <div className="min-h-screen flex flex-col bg-[#FAF7F2] text-stone-900">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-white px-3 py-2 rounded z-[60]">Skip to content</a>
      <Header />
      <main id="main" className="flex-1"><Outlet /></main>
      <Footer />
    </div>
  );
}
