import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Plus, Gift, MailCheck, Lock, ChevronRight } from "lucide-react";
import { useLang } from "../lib/i18n";
import { useAuth } from "../lib/auth";
import { api, errMsg, fmtDate, fmtMoney } from "../lib/api";
import { Loading } from "../components/ProtectedRoute";
import { MaskedCode, StatusBadge } from "../components/GiftBits";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";

const NewGiftBtn = () => {
  const { t } = useLang();
  return (
    <Link to="/gifts/new" data-testid="dashboard-new-gift-btn" className="inline-flex items-center gap-2 bg-[#D95D39] hover:bg-[#C24C29] text-white font-semibold px-6 py-3 rounded-full transition-colors active:scale-[0.98]">
      <Plus size={18} />{t("dash.new")}
    </Link>
  );
};

const Empty = () => {
  const { t } = useLang();
  return (
    <div data-testid="dashboard-empty-state" className="bg-white border border-dashed border-stone-300 rounded-2xl p-8 sm:p-12 text-center">
      <span className="mx-auto grid place-items-center h-14 w-14 rounded-full bg-[#FDF2EE] text-[#D95D39]"><Gift size={26} /></span>
      <h2 className="font-serif text-2xl mt-4">{t("dash.empty_title")}</h2>
      <p className="text-stone-600 mt-2 max-w-md mx-auto">{t("dash.empty_body")}</p>
      <div className="mt-6"><NewGiftBtn /></div>
    </div>
  );
};

const Stat = ({ label, value, testId }) => (
  <div className="bg-white border border-stone-200/80 rounded-2xl p-4 sm:p-5">
    <p className="text-xs font-semibold uppercase tracking-widest text-stone-500">{label}</p>
    <p className="font-serif text-2xl sm:text-3xl mt-1 text-stone-900" data-testid={testId}>{value}</p>
  </div>
);

const GiftCard = ({ g, i }) => {
  const { t, lang } = useLang();
  const [busy, setBusy] = useState(false);
  const resend = async () => {
    setBusy(true);
    try { await api.post(`/gifts/mine/${g.id}/resend-email`); toast.success(t("dash.resent")); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <article data-testid={`gift-row-${i}`} className="bg-white border border-stone-200/80 rounded-2xl p-5 sm:p-6 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge status={g.display_status} testId={`gift-status-badge-${i}`} />
            {g.demo && <span className="text-[10px] font-bold tracking-widest bg-amber-100 text-amber-900 px-2 py-0.5 rounded">{t("common.demo")}</span>}
            {g.locked && <span className="inline-flex items-center gap-1 text-xs font-semibold text-red-800"><Lock size={12} />{t("dash.locked")}</span>}
            {g.email_status === "failed" && <span className="text-xs font-semibold text-red-800">{t("dash.email_failed")}</span>}
          </div>
          <p className="text-sm text-stone-500">{fmtDate(g.created_at, lang)}{g.recipient_first_name && <> · {t("dash.for")} <strong className="text-stone-800">{g.recipient_first_name}</strong></>}</p>
        </div>
        <div className="sm:text-right">
          <p className="text-xs text-stone-500">{t("dash.balance")} / {t("dash.original")}</p>
          <p className="font-semibold text-stone-900" data-testid={`gift-balance-${i}`}>{fmtMoney(g.balance, lang)} <span className="text-stone-500 font-normal">/ {fmtMoney(g.amount, lang)}</span></p>
        </div>
      </div>
      <div className="mt-4"><MaskedCode code={g.code} prefix={`gift-${i}`} /></div>
      <div className="mt-4 border-t border-stone-100 pt-3">
        <p className="text-xs font-semibold uppercase tracking-widest text-stone-500 mb-2">{t("dash.uses")}</p>
        {g.redemptions.length === 0 ? <p className="text-sm text-stone-500">{t("dash.no_uses")}</p> : (
          <ul className="space-y-1.5" data-testid={`gift-redemptions-${i}`}>
            {g.redemptions.map((r) => (
              <li key={r.id} className="text-sm flex flex-wrap justify-between gap-2">
                <span className="text-stone-800">{r.course_name}</span>
                <span className="text-stone-600">−{fmtMoney(r.amount_used, lang)} · {fmtDate(r.created_at, lang)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <Link to={`/gifts/${g.id}`} data-testid={`gift-view-btn-${i}`} className="inline-flex items-center gap-1 px-4 py-2 rounded-lg border border-stone-300 hover:bg-stone-50 text-sm font-medium">{t("dash.view")}<ChevronRight size={16} /></Link>
        <button type="button" onClick={resend} disabled={busy} data-testid={`gift-resend-email-btn-${i}`} className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-stone-300 hover:bg-stone-50 text-sm font-medium disabled:opacity-60"><MailCheck size={16} />{t("dash.resend")}</button>
      </div>
    </article>
  );
};

const GiftsTab = () => {
  const { t, lang } = useLang();
  const [gifts, setGifts] = useState(null);
  useEffect(() => {
    api.get("/gifts/mine").then(({ data }) => setGifts(data)).catch(() => setGifts([]));
  }, []);
  if (!gifts) return <Loading />;
  if (!gifts.length) return <Empty />;
  const total = gifts.reduce((s, g) => s + g.amount, 0);
  const remaining = gifts.reduce((s, g) => s + g.balance, 0);
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-3 sm:gap-4">
        <Stat label={t("dash.gifts_count")} value={gifts.length} testId="stat-gifts-count" />
        <Stat label={t("dash.total_given")} value={fmtMoney(total, lang)} testId="stat-total-given" />
        <Stat label={t("dash.remaining")} value={fmtMoney(remaining, lang)} testId="stat-remaining" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="dashboard-gifts-table">
        {gifts.map((g, i) => <GiftCard key={g.id} g={g} i={i} />)}
      </div>
    </div>
  );
};

const AccountTab = () => {
  const { t } = useLang();
  const { user, logout, refresh } = useAuth();
  const navigate = useNavigate();
  const [cur, setCur] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [error, setError] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (pw !== pw2) return setError(t("login.mismatch"));
    try {
      await api.post("/auth/change-password", { current_password: cur || null, new_password: pw });
      toast.success(t("acct.updated"));
      setCur(""); setPw(""); setPw2("");
      refresh();
    } catch (err) { setError(errMsg(err)); }
  };
  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div className="bg-white border border-stone-200/80 rounded-2xl p-6">
        <p className="text-xs font-semibold uppercase tracking-widest text-stone-500">{t("acct.email")}</p>
        <p className="mt-1 text-lg font-medium break-all" data-testid="account-email">{user.email}</p>
        <button type="button" onClick={async () => { await logout(); navigate("/"); }} data-testid="account-logout-btn" className="mt-6 px-5 py-2.5 rounded-xl border border-stone-300 hover:bg-stone-50 font-medium">{t("acct.logout")}</button>
      </div>
      <form onSubmit={submit} className="bg-white border border-stone-200/80 rounded-2xl p-6 space-y-4" data-testid="change-password-form">
        <h2 className="font-serif text-2xl">{user.password_set ? t("acct.change_pw") : t("acct.set_pw")}</h2>
        {!user.password_set && <p className="text-sm text-stone-600">{t("acct.set_pw_hint")}</p>}
        {user.password_set && (
          <div className="space-y-1.5"><Label htmlFor="cp-cur">{t("acct.current")}</Label>
            <Input id="cp-cur" type="password" required value={cur} onChange={(e) => setCur(e.target.value)} className="h-11" data-testid="change-password-current-input" /></div>
        )}
        <div className="space-y-1.5"><Label htmlFor="cp-new">{t("acct.new")}</Label>
          <Input id="cp-new" type="password" minLength={8} required value={pw} onChange={(e) => setPw(e.target.value)} className="h-11" data-testid="change-password-new-input" />
          <p className="text-xs text-stone-500">{t("login.password_hint")}</p></div>
        <div className="space-y-1.5"><Label htmlFor="cp-new2">{t("acct.confirm")}</Label>
          <Input id="cp-new2" type="password" minLength={8} required value={pw2} onChange={(e) => setPw2(e.target.value)} className="h-11" data-testid="change-password-confirm-input" /></div>
        {error && <p role="alert" className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg p-3" data-testid="change-password-error">{error}</p>}
        <button type="submit" data-testid="change-password-submit-btn" className="px-6 py-3 rounded-xl bg-[#2A4736] hover:bg-[#1E3527] text-white font-semibold">{t("common.save")}</button>
      </form>
    </div>
  );
};

export default function Dashboard() {
  const { t } = useLang();
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-10" data-testid="dashboard-page">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-serif text-4xl sm:text-5xl text-stone-900">{t("dash.title")}</h1>
          <p className="text-stone-600 mt-2">{t("dash.subtitle")}</p>
        </div>
        <NewGiftBtn />
      </div>
      <Tabs defaultValue="gifts" className="mt-8">
        <TabsList className="bg-stone-100 p-1 rounded-xl h-auto">
          <TabsTrigger value="gifts" data-testid="dashboard-gifts-tab" className="rounded-lg px-4 py-2">{t("dash.tab_gifts")}</TabsTrigger>
          <TabsTrigger value="account" data-testid="dashboard-account-tab" className="rounded-lg px-4 py-2">{t("dash.tab_account")}</TabsTrigger>
        </TabsList>
        <TabsContent value="gifts" className="pt-6"><GiftsTab /></TabsContent>
        <TabsContent value="account" className="pt-6"><AccountTab /></TabsContent>
      </Tabs>
    </div>
  );
}
