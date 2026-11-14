import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { Menu, Gift, LogOut, LayoutDashboard, Shield } from "lucide-react";
import { useAuth } from "../lib/auth";
import { useLang } from "../lib/i18n";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "./ui/sheet";

export const Logo = () => (
  <Link to="/" data-testid="header-logo" className="flex items-center gap-2.5 shrink-0" aria-label="giftaol.ca home">
    <img src="/logo.png" alt="The Art of Living Canada" className="h-11 sm:h-12 w-auto" data-testid="header-logo-img" />
    <span className="hidden lg:inline font-serif text-xl text-[#2A4736] leading-none border-l border-stone-300 pl-2.5">gift<span className="text-[#D95D39]">aol</span><span className="text-stone-500 text-base">.ca</span></span>
  </Link>
);

export const LangSwitch = () => {
  const { lang, setLang, t } = useLang();
  const { user } = useAuth();
  const choose = (l) => {
    setLang(l);
    if (user) {
      import("../lib/api").then(({ api }) => api.put("/auth/me/lang", { lang: l }).catch(() => {}));
    }
  };
  return (
    <div role="group" aria-label={t("nav.lang")} className="flex rounded-full border border-stone-300 p-0.5 bg-white">
      {["en", "fr"].map((l) => (
        <button key={l} type="button" data-testid={`language-switcher-${l}-btn`} aria-pressed={lang === l}
          onClick={() => choose(l)}
          className={`px-3 py-1 text-xs font-semibold rounded-full transition-colors ${lang === l ? "bg-[#2A4736] text-white" : "text-stone-700 hover:bg-stone-100"}`}>
          {l.toUpperCase()}
        </button>
      ))}
    </div>
  );
};

const NavItems = ({ onNav, mobile }) => {
  const { user, logout } = useAuth();
  const { t } = useLang();
  const navigate = useNavigate();
  const cls = ({ isActive }) =>
    `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${isActive ? "text-[#C24C29] bg-[#FDF2EE]" : "text-stone-700 hover:text-stone-950 hover:bg-stone-100"}`;
  const sfx = mobile ? "-mobile" : "";
  return (
    <>
      <NavLink to="/gifts/new" className={cls} onClick={onNav} data-testid={`nav-give-link${sfx}`}><Gift size={16} />{t("nav.give")}</NavLink>
      {user && <NavLink to="/dashboard" className={cls} onClick={onNav} data-testid={`nav-dashboard-link${sfx}`}><LayoutDashboard size={16} />{t("nav.dashboard")}</NavLink>}
      {user?.is_admin && <NavLink to="/admin" className={cls} onClick={onNav} data-testid={`nav-admin-link${sfx}`}><Shield size={16} />{t("nav.admin")}</NavLink>}
      {user ? (
        <button type="button" data-testid={`nav-logout-btn${sfx}`} onClick={async () => { onNav?.(); await logout(); navigate("/"); }}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-stone-700 hover:bg-stone-100">
          <LogOut size={16} />{t("nav.logout")}
        </button>
      ) : (
        <Link to="/login" onClick={onNav} data-testid={`nav-login-btn${sfx}`}
          className="px-5 py-2 rounded-full bg-[#2A4736] hover:bg-[#1E3527] text-white text-sm font-semibold transition-colors text-center">
          {t("nav.login")}
        </Link>
      )}
    </>
  );
};

export const Header = () => {
  const [open, setOpen] = useState(false);
  const { t } = useLang();
  return (
    <header className="bg-white/90 backdrop-blur-xl border-b border-stone-200/70 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 h-16 flex items-center justify-between gap-3">
        <Logo />
        <nav className="hidden md:flex items-center gap-1" aria-label="Main">
          <NavItems />
          <div className="ml-2"><LangSwitch /></div>
        </nav>
        <div className="flex md:hidden items-center gap-2">
          <LangSwitch />
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button type="button" data-testid="mobile-menu-trigger" aria-label={t("nav.menu")} className="p-2 rounded-lg hover:bg-stone-100"><Menu size={22} /></button>
            </SheetTrigger>
            <SheetContent side="right" className="bg-white w-72">
              <SheetTitle className="font-serif text-xl text-[#2A4736] mb-4">giftaol.ca</SheetTitle>
              <div className="flex flex-col gap-1"><NavItems onNav={() => setOpen(false)} mobile /></div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
};
