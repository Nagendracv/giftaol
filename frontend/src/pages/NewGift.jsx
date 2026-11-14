import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Info, FlaskConical, Clock } from "lucide-react";
import { useLang } from "../lib/i18n";
import { useSite } from "../lib/site";
import { api, errMsg, fmtMoney } from "../lib/api";
import { useAuth } from "../lib/auth";
import { Turnstile } from "../components/Turnstile";
import { CheckCircle2 } from "lucide-react";
import { Loading } from "../components/ProtectedRoute";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";

const useRange = () => {
  const { config } = useSite();
  const { t, lang } = useLang();
  if (!config) return {};
  const min = config.min_amount, max = config.max_amount;
  const text = max ? t("new.range_both", { min: fmtMoney(min, lang), max: fmtMoney(max, lang) }) : t("new.range_min", { min: fmtMoney(min, lang) });
  return { min, max, text, valid: (a) => a >= min && (!max || a <= max) };
};

const GuestEmail = ({ form, setForm, setToken, reset }) => {
  const { t } = useLang();
  return (
    <div className="space-y-2 rounded-xl border border-stone-200 bg-white p-4" data-testid="guest-email-section">
      <Label htmlFor="ng-email" className="text-sm font-medium">{t("new.your_email")}</Label>
      <Input id="ng-email" type="email" autoComplete="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
        className="h-12 bg-white" data-testid="gift-giver-email-input" aria-describedby="ng-email-note" />
      <p id="ng-email-note" className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-md px-2.5 py-1.5" data-testid="gift-giver-email-note">{t("new.your_email_note")}</p>
      <Turnstile onToken={setToken} resetKey={reset} testId="gift-turnstile-container" />
    </div>
  );
};

const DetailsStep = ({ form, setForm, onNext }) => {
  const { t, lang } = useLang();
  const { config } = useSite();
  const { user } = useAuth();
  const range = useRange();
  const [error, setError] = useState("");
  const [limitMsg, setLimitMsg] = useState("");
  const [token, setToken] = useState("");
  const [reset, setReset] = useState(0);
  const [busy, setBusy] = useState(false);
  const presets = [100, 150, 250, 500].filter((p) => range.valid(p));
  const submit = async (e) => {
    e.preventDefault();
    setLimitMsg("");
    const a = parseFloat(form.amount);
    if (!a || !range.valid(a)) return setError(t("new.out_of_range", { range: range.text }));
    setError("");
    if (user) return onNext("payment");
    if (!token) return setError(t("login.captcha_needed"));
    setBusy(true);
    try {
      const { data } = await api.post("/auth/request-code", { email: form.email, turnstile_token: token });
      onNext("verify", data.has_password);
    } catch (err) {
      if (err?.response?.data?.detail?.code === "daily_limit") setLimitMsg(err.response.data.detail.message);
      else setError(errMsg(err));
      setToken("");
      setReset((r) => r + 1);
    } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-6" data-testid="new-gift-form">
      <div className="space-y-2">
        <Label htmlFor="ng-amount" className="text-sm font-medium">{t("new.amount")}</Label>
        {presets.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {presets.map((p) => (
              <button key={p} type="button" data-testid={`gift-amount-preset-${p}`} onClick={() => setForm({ ...form, amount: String(p) })}
                className={`px-4 py-2 rounded-full border text-sm font-semibold transition-colors ${String(p) === form.amount ? "bg-[#2A4736] text-white border-[#2A4736]" : "bg-white border-stone-300 hover:border-stone-500"}`}>
                {fmtMoney(p, lang)}
              </button>
            ))}
          </div>
        )}
        <Input id="ng-amount" type="number" inputMode="decimal" step="0.01" min="0" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })}
          className="h-12 text-lg bg-white" data-testid="gift-amount-custom-input" aria-describedby="ng-range" />
        <p id="ng-range" className="text-xs text-stone-500" data-testid="gift-amount-range">{t("new.range", { range: range.text })}</p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="ng-msg" className="text-sm font-medium">{t("new.message")} <span className="text-stone-500 font-normal">({t("common.optional")})</span></Label>
        <Textarea id="ng-msg" maxLength={500} rows={4} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="bg-white text-base" data-testid="gift-message-textarea" />
        <div className="flex justify-between text-xs text-stone-500"><span>{t("new.message_hint")}</span><span data-testid="gift-message-counter">{form.message.length}/500</span></div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="ng-name" className="text-sm font-medium">{t("new.recipient")} <span className="text-stone-500 font-normal">({t("common.optional")})</span></Label>
        <Input id="ng-name" maxLength={60} value={form.recipient_first_name} onChange={(e) => setForm({ ...form, recipient_first_name: e.target.value })} className="h-12 bg-white" data-testid="gift-recipient-name-input" />
        <p className="text-xs text-stone-500">{t("new.recipient_hint")}</p>
      </div>
      <div className="flex gap-3 rounded-xl bg-[#FDF2EE] border border-[#F4CDBE] p-4" data-testid="discount-explainer">
        <Info size={20} className="text-[#C24C29] shrink-0 mt-0.5" />
        <div><p className="font-semibold text-sm text-stone-900">{t("new.how")}</p><p className="text-sm text-stone-700 mt-1 leading-relaxed">{config.texts.explainer[lang]}</p></div>
      </div>
      {!user && <GuestEmail form={form} setForm={setForm} setToken={setToken} reset={reset} />}
      {limitMsg && <p role="alert" data-testid="code-limit-message" className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-3">{limitMsg}</p>}
      {error && <p role="alert" className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg p-3" data-testid="gift-amount-error">{error}</p>}
      <button type="submit" disabled={busy} data-testid="gift-proceed-payment-btn" className="w-full h-12 rounded-xl bg-[#D95D39] hover:bg-[#C24C29] disabled:opacity-60 text-white font-semibold transition-colors">
        {busy ? t("common.loading") : user ? t("new.continue") : t("new.continue_next")}
      </button>
    </form>
  );
};

const PasswordOption = ({ email, onVerified }) => {
  const { t } = useLang();
  const [pw, setPw] = useState("");
  const [token, setToken] = useState("");
  const [reset, setReset] = useState(0);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!token) return setError(t("login.captcha_needed"));
    setBusy(true);
    try {
      const { data } = await api.post("/auth/login", { email, password: pw, turnstile_token: token });
      onVerified(data);
    } catch (err) {
      setError(errMsg(err)); setToken(""); setReset((r) => r + 1);
    } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-3" data-testid="gift-password-option-form">
      <Label htmlFor="vs-pw" className="text-sm font-medium">{t("login.password")}</Label>
      <Input id="vs-pw" type="password" autoComplete="current-password" required value={pw} onChange={(e) => setPw(e.target.value)} className="h-12 bg-white" data-testid="gift-verify-password-input" />
      <Turnstile onToken={setToken} resetKey={reset} testId="gift-password-turnstile-container" />
      {error && <p role="alert" className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg p-3" data-testid="gift-password-error">{error}</p>}
      <button type="submit" disabled={busy} data-testid="gift-verify-password-btn" className="h-12 px-5 rounded-xl bg-[#2A4736] hover:bg-[#1E3527] disabled:opacity-60 text-white font-semibold">
        {busy ? t("common.loading") : t("verify.pw_btn")}
      </button>
    </form>
  );
};

const MethodToggle = ({ method, setMethod }) => {
  const { t } = useLang();
  return (
    <div className="grid grid-cols-2 rounded-xl bg-stone-100 p-1" role="group" aria-label={t("verify.choose")} data-testid="gift-verify-method-toggle">
      {[["code", t("verify.use_code")], ["password", t("verify.use_password")]].map(([m, l]) => (
        <button key={m} type="button" onClick={() => setMethod(m)} aria-pressed={method === m} data-testid={`gift-verify-method-${m}`}
          className={`rounded-lg py-2 px-2 text-sm font-medium transition-colors ${method === m ? "bg-white shadow-sm text-stone-900" : "text-stone-600"}`}>{l}</button>
      ))}
    </div>
  );
};

const VerifyStep = ({ email, hasPassword, onBack, onNext }) => {
  const { t } = useLang();
  const { setUser } = useAuth();
  const [code, setCode] = useState("");
  const [method, setMethod] = useState("code");
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const done = (u) => { setUser(u); setVerified(true); };
  const verify = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      const { data } = await api.post("/auth/verify-code-login", { email, code });
      done(data);
    } catch (err) { setError(errMsg(err)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-5" data-testid="verify-step">
      <p className="text-[#1E3527] bg-[#EBF2ED] border border-[#2A4736]/20 rounded-xl p-4 leading-relaxed" data-testid="verify-step-message">
        {t("verify.sent")} <strong className="break-all">({email})</strong>
        {hasPassword && <span className="block mt-2 text-sm" data-testid="verify-registered-note">{t("verify.registered")}</span>}
      </p>
      {hasPassword && !verified && <MethodToggle method={method} setMethod={setMethod} />}
      {hasPassword && method === "password" && !verified ? <PasswordOption email={email} onVerified={done} /> : (
      <form onSubmit={verify} className="space-y-3">
        <Label htmlFor="vs-code" className="text-sm font-medium">{t("login.code")}</Label>
        <div className="flex gap-2">
          <Input id="vs-code" inputMode="numeric" autoComplete="one-time-code" required disabled={verified} value={code} onChange={(e) => setCode(e.target.value)}
            className="h-12 bg-white text-lg tracking-widest" data-testid="gift-verify-code-input" />
          <button type="submit" disabled={busy || verified} data-testid="gift-verify-code-btn" className="h-12 px-5 rounded-xl bg-[#2A4736] hover:bg-[#1E3527] disabled:opacity-60 text-white font-semibold shrink-0">
            {busy ? t("common.loading") : t("verify.btn")}
          </button>
        </div>
      </form>
      )}
      {verified && <p className="flex items-center gap-2 text-green-800 font-medium" data-testid="gift-verify-success"><CheckCircle2 size={18} />{t("verify.ok")}</p>}
      {error && <p role="alert" className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg p-3" data-testid="gift-verify-error">{error}</p>}
      <button type="button" onClick={onNext} disabled={!verified} data-testid="gift-verified-continue-payment-btn"
        className="w-full h-12 rounded-xl bg-[#D95D39] hover:bg-[#C24C29] disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold transition-colors">
        {t("new.continue")}
      </button>
      {!verified && <button type="button" onClick={onBack} data-testid="gift-verify-back-btn" className="text-sm text-[#2A4736] underline underline-offset-4">{t("verify.change")}</button>}
    </div>
  );
};

const PaymentStep = ({ form, onBack }) => {
  const { t, lang } = useLang();
  const { config } = useSite();
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const amount = parseFloat(form.amount);
  const pay = async () => {
    setBusy(true); setError("");
    try {
      const { data: co } = await api.post("/gifts/checkout", { amount, message: form.message || null, recipient_first_name: form.recipient_first_name || null });
      const { data: gift } = await api.post(`/payments/${co.payment_id}/demo-confirm`);
      navigate(`/gifts/${gift.id}?new=1`, { replace: true });
    } catch (e) { setError(errMsg(e)); setBusy(false); }
  };
  return (
    <div className="space-y-6" data-testid="payment-step">
      <div className="flex justify-between items-center bg-white border border-stone-200 rounded-xl p-4">
        <span className="text-stone-600">{t("pay.summary")}</span>
        <span className="font-serif text-2xl" data-testid="payment-amount">{fmtMoney(amount, lang)}</span>
      </div>
      {config.demo_payments ? (
        <div className="rounded-xl border-2 border-dashed border-amber-400 bg-amber-50 p-5" data-testid="demo-payment-warning-banner">
          <p className="flex items-center gap-2 font-bold text-amber-950"><FlaskConical size={18} />{t("pay.demo_title")}</p>
          <p className="text-sm text-amber-900 mt-2 leading-relaxed">{t("pay.demo_body")}</p>
        </div>
      ) : (
        <div className="rounded-xl border border-stone-300 bg-stone-50 p-5" data-testid="payment-placeholder-notice">
          <p className="flex items-center gap-2 font-semibold text-stone-900"><Clock size={18} />{t("pay.unavailable")}</p>
          <p className="text-sm text-stone-700 mt-2">{config.texts.payment_placeholder[lang]}</p>
        </div>
      )}
      {error && <p role="alert" className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg p-3" data-testid="payment-error">{error}</p>}
      <p className="text-sm text-stone-600" data-testid="payment-providers-note">{t("pay.providers_note")}</p>
      <div className="flex flex-col-reverse sm:flex-row gap-3">
        <button type="button" onClick={onBack} data-testid="payment-back-btn" className="h-12 px-6 rounded-xl border border-stone-300 hover:bg-stone-50 font-medium">{t("common.back")}</button>
        <button type="button" onClick={pay} disabled={busy || !config.demo_payments} data-testid="demo-payment-submit-btn"
          className="w-full sm:flex-1 min-h-12 h-12 rounded-xl bg-[#2A4736] hover:bg-[#1E3527] disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold transition-colors">
          {busy ? t("pay.processing") : t("pay.pay", { amount: fmtMoney(amount, lang) })}{config.demo_payments && ` (${t("common.demo")})`}
        </button>
      </div>
    </div>
  );
};

export default function NewGift() {
  const { t } = useLang();
  const { config } = useSite();
  const { user } = useAuth();
  const [step, setStep] = useState("details");
  const [form, setForm] = useState({ amount: "", message: "", recipient_first_name: "", email: "" });
  const [guestFlow, setGuestFlow] = useState(false);
  const [hasPassword, setHasPassword] = useState(false);
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [step]);
  if (!config || user === null) return <Loading />;
  const steps = guestFlow || !user ? ["details", "verify", "payment"] : ["details", "payment"];
  const title = { details: t("new.title"), verify: t("verify.title"), payment: t("pay.title") }[step];
  return (
    <div className="max-w-xl mx-auto px-4 py-10 sm:py-14" data-testid="new-gift-page">
      <p className="text-xs font-semibold uppercase tracking-widest text-[#C24C29]" data-testid="gift-step-indicator">{steps.indexOf(step) + 1} / {steps.length}</p>
      <h1 className="font-serif text-4xl sm:text-5xl text-stone-900 mt-1">{title}</h1>
      {step === "details" && <p className="text-stone-600 mt-2">{t("new.subtitle")}</p>}
      <div className="mt-8">
        {step === "details" && <DetailsStep form={form} setForm={setForm} onNext={(s, hp) => { if (s === "verify") { setGuestFlow(true); setHasPassword(!!hp); } setStep(s); }} />}
        {step === "verify" && <VerifyStep email={form.email} hasPassword={hasPassword} onBack={() => setStep("details")} onNext={() => setStep("payment")} />}
        {step === "payment" && <PaymentStep form={form} onBack={() => setStep("details")} />}
      </div>
    </div>
  );
}
