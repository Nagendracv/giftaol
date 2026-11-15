import { useState } from "react";
import { Link, Outlet } from "react-router-dom";
import { Show, UserButton } from "@clerk/react";
import { Gift } from "lucide-react";
import { useSite } from "@/lib/site";

function LanguageSwitcher() {
  const { site, setLocale, t } = useSite();
  return (
    <div role="group" aria-label={t("languageLabel")} className="flex rounded-full border border-stone-200 p-[3px]" data-testid="language-switcher">
      {site.locales.map((code) => (
        <button
          key={code}
          type="button"
          lang={code}
          aria-pressed={site.locale === code}
          onClick={() => setLocale(code)}
          data-testid={`lang-switch-${code}`}
          className={`rounded-full px-3 py-1 text-[13px] font-semibold transition-colors ${
            site.locale === code ? "bg-amber-100 text-amber-900" : "text-stone-600 hover:text-stone-900"
          }`}
        >
          {code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}

export const fill = (template, values) => Object.entries(values).reduce((s, [k, v]) => s.replaceAll(`{${k}}`, v), template);
const siteName = (site, t) => fill(t("siteName"), { city: site.city.displayName });

function SiteFooter() {
  const { site, t } = useSite();
  const { contactEmail, contactPhone } = site.city;
  return (
    <footer className="mt-10 border-t border-stone-200 bg-white" data-testid="site-footer">
      <div className="mx-auto grid max-w-[1100px] gap-2 px-6 pb-24 pt-7 text-sm text-stone-600">
        <nav aria-label={t("footerNav")} className="flex gap-5">
          <a href="/privacy" className="text-amber-800 hover:underline" data-testid="footer-privacy-link">{t("privacyTitle")}</a>
          <a href="/terms" className="text-amber-800 hover:underline" data-testid="footer-terms-link">{t("termsTitle")}</a>
        </nav>
        {(contactEmail || contactPhone) && (
          <p>{contactEmail && <a href={`mailto:${contactEmail}`} className="text-amber-800">{contactEmail}</a>}{contactEmail && contactPhone && " · "}{contactPhone && <a href={`tel:${contactPhone}`} className="text-amber-800">{contactPhone}</a>}</p>
        )}
        <p>© {new Date().getFullYear()} {siteName(site, t)} · {t("placesCredit")} <a href="https://www.geonames.org" target="_blank" rel="noopener noreferrer" className="text-amber-800" data-testid="footer-geonames-credit">GeoNames</a></p>
      </div>
    </footer>
  );
}

function CookieNotice() {
  const { t } = useSite();
  const [shown, setShown] = useState(() => !document.cookie.split("; ").includes("cookie_ok=1"));
  if (!shown) return null;
  const ok = () => { document.cookie = "cookie_ok=1; path=/; max-age=31536000; samesite=lax"; setShown(false); };
  return (
    <div role="region" aria-label={t("cookieLabel")} data-testid="cookie-notice"
      className="fixed inset-x-4 bottom-4 z-50 mx-auto flex max-w-[640px] items-center gap-4 rounded-2xl bg-stone-900 px-4 py-3.5 text-stone-50 shadow-xl">
      <p className="flex-1 text-sm">{t("cookieText")} <a href="/privacy" className="text-amber-300 underline">{t("privacyTitle")}</a></p>
      <button type="button" className="btn-primary" onClick={ok} data-testid="cookie-notice-ok-button">{t("cookieOk")}</button>
    </div>
  );
}

export function SiteHeader() {
  const { site, t } = useSite();
  return (
    <header className="sticky top-0 z-40 border-b border-stone-200 bg-white" data-testid="main-header">
      <div className="mx-auto flex max-w-[1200px] items-center justify-between gap-4 px-6 py-3.5">
        <a href="/" data-testid="header-logo-link" className="focus-ring rounded">
          <span className="flex items-center gap-3">
            <img src={site.city?.logoUrl || site.defaultLogo} alt={t("logoAlt")} className="h-9 w-auto sm:h-11" data-testid="header-logo" />
            <span className="hidden border-l border-stone-200 pl-3 font-heading text-[17px] font-semibold text-stone-900 sm:inline" data-testid="header-site-name">
              {siteName(site, t)}
            </span>
          </span>
        </a>
        <div className="flex items-center gap-3">
          <Link to="/gift" aria-label={t("giftButton")} data-testid="header-give-gift-link"
            className="inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-semibold text-stone-800 transition-colors hover:bg-amber-50 hover:text-amber-900">
            <Gift className="h-[17px] w-[17px]" aria-hidden="true" /><span className="hidden sm:inline">{t("giftButton")}</span>
          </Link>
          <Show when="signed-out">
            <Link to="/sign-in" className="btn-primary whitespace-nowrap" data-testid="auth-button"><span className="hidden sm:inline">{t("signInButton")}</span><span className="sm:hidden">{t("signInShort")}</span></Link>
          </Show>
          <Show when="signed-in">
            <Link to="/dashboard" className="hidden text-sm font-semibold text-stone-700 hover:text-amber-800 sm:inline" data-testid="header-dashboard-link">
              {t("dashboardLink")}
            </Link>
            <UserButton />
          </Show>
          <LanguageSwitcher />
        </div>
      </div>
    </header>
  );
}

export function NotConfigured() {
  const { t } = useSite();
  return (
    <main className="mx-auto mt-[18vh] max-w-[520px] rounded-2xl border border-stone-200 bg-white p-10" data-testid="not-found-container">
      <h1 className="font-heading text-2xl font-semibold sm:text-3xl" data-testid="not-found-title">{t("notConfiguredTitle")}</h1>
      <p className="mt-3 text-stone-600">{t("notConfiguredMessage")}</p>
    </main>
  );
}

export function SiteLayout() {
  const { site } = useSite();
  if (!site.configured) return <NotConfigured />;
  return (
    <div className="flex min-h-screen flex-col bg-[#FAF9F6]">
      <SiteHeader />
      <div className="flex-1"><Outlet /></div>
      <SiteFooter />
      <CookieNotice />
    </div>
  );
}
