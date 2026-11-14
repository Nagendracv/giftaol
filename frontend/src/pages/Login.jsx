import { useState } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "../lib/auth";
import { useLang } from "../lib/i18n";
import { useSite } from "../lib/site";
import { api, errMsg } from "../lib/api";
import { Turnstile } from "../components/Turnstile";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";

const safeNext = (n) => (n && n.startsWith("/") && !n.startsWith("//") ? n : "/dashboard");

const Field = ({ id, label, hint, ...props }) => (
  <div className="space-y-1.5">
    <Label htmlFor={id} className="text-sm font-medium text-stone-800">{label}</Label>
    <Input id={id} className="h-12 bg-white border-stone-300 text-base" {...props} />
    {hint && <p className="text-xs text-stone-500">{hint}</p>}
  </div>
);

const ErrorBox = ({ text, testId }) => text ? <p role="alert" data-testid={testId} className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg p-3">{text}</p> : null;

const PrimaryBtn = ({ children, ...p }) => (
  <button {...p} className="w-full h-12 rounded-xl bg-[#D95D39] hover:bg-[#C24C29] disabled:opacity-60 text-white font-semibold transition-colors active:scale-[0.99]">{children}</button>
);

const PasswordLogin = ({ onDone }) => {
  const { t } = useLang();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
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
      const { data } = await api.post("/auth/login", { email, password, turnstile_token: token });
      onDone(data);
    } catch (err) {
      setError(errMsg(err));
      setToken("");
      setReset((r) => r + 1);
    } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-4" data-testid="password-login-form">
      <Field id="li-email" label={t("login.email")} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="auth-email-input" />
      <Field id="li-pw" label={t("login.password")} type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} data-testid="auth-password-input" />
      <Turnstile onToken={setToken} resetKey={reset} testId="login-turnstile-container" />
      <ErrorBox text={error} testId="login-error" />
      <PrimaryBtn type="submit" disabled={busy} data-testid="auth-login-submit-btn">{busy ? t("common.loading") : t("login.submit")}</PrimaryBtn>
      <p className="text-sm text-stone-600">{t("login.no_password")}</p>
    </form>
  );
};

const RequestCode = ({ email, setEmail, onSent }) => {
  const { t } = useLang();
  const [token, setToken] = useState("");
  const [reset, setReset] = useState(0);
  const [error, setError] = useState("");
  const [limitMsg, setLimitMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setError(""); setLimitMsg("");
    if (!token) return setError(t("login.captcha_needed"));
    setBusy(true);
    try {
      await api.post("/auth/request-code", { email, turnstile_token: token });
      onSent();
    } catch (err) {
      if (err?.response?.data?.detail?.code === "daily_limit") setLimitMsg(err.response.data.detail.message);
      else setError(errMsg(err));
    } finally {
      setBusy(false); setToken(""); setReset((r) => r + 1);
    }
  };
  return (
    <form onSubmit={submit} className="space-y-4" data-testid="request-code-form">
      <p className="text-sm text-stone-600">{t("login.code_intro")}</p>
      <Field id="rc-email" label={t("login.email")} type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} data-testid="auth-code-email-input" />
      <Turnstile onToken={setToken} resetKey={reset} />
      {limitMsg && <p role="alert" data-testid="code-limit-message" className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-3">{limitMsg}</p>}
      <ErrorBox text={error} testId="request-code-error" />
      <PrimaryBtn type="submit" disabled={busy} data-testid="auth-send-code-btn">{busy ? t("common.loading") : t("login.send_code")}</PrimaryBtn>
    </form>
  );
};

const VerifyCode = ({ email, onBack, onDone }) => {
  const { t } = useLang();
  const [code, setCode] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (pw !== pw2) return setError(t("login.mismatch"));
    setBusy(true);
    try {
      const { data } = await api.post("/auth/verify-code", { email, code, password: pw });
      onDone(data);
    } catch (err) { setError(errMsg(err)); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-4" data-testid="verify-code-form">
      <p className="text-sm text-[#1E3527] bg-[#EBF2ED] rounded-lg p-3" data-testid="code-sent-message">{t("login.code_sent", { email })}</p>
      <Field id="vc-code" label={t("login.code")} inputMode="numeric" autoComplete="one-time-code" required value={code} onChange={(e) => setCode(e.target.value)} data-testid="auth-otp-input" />
      <Field id="vc-pw" label={t("login.new_password")} hint={t("login.password_hint")} type="password" autoComplete="new-password" minLength={8} required value={pw} onChange={(e) => setPw(e.target.value)} data-testid="auth-new-password-input" />
      <Field id="vc-pw2" label={t("login.confirm_password")} type="password" autoComplete="new-password" minLength={8} required value={pw2} onChange={(e) => setPw2(e.target.value)} data-testid="auth-confirm-password-input" />
      <ErrorBox text={error} testId="verify-code-error" />
      <PrimaryBtn type="submit" disabled={busy} data-testid="auth-verify-code-btn">{busy ? t("common.loading") : t("login.verify")}</PrimaryBtn>
      <button type="button" onClick={onBack} data-testid="auth-use-other-email-btn" className="text-sm text-[#2A4736] underline underline-offset-4">{t("login.resend")} / {t("login.use_other_email")}</button>
    </form>
  );
};

const GoogleButton = ({ next }) => {
  const { t } = useLang();
  const go = () => {
    sessionStorage.setItem("giftaol_next", next);
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/dashboard";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return (
    <button type="button" onClick={go} data-testid="auth-google-login-btn" className="w-full h-12 rounded-xl border border-stone-300 bg-white hover:bg-stone-50 font-semibold text-stone-800 flex items-center justify-center gap-3 transition-colors">
      <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" /><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" /><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" /><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" /></svg>
      {t("login.google")}
    </button>
  );
};

export default function Login() {
  const { user, setUser } = useAuth();
  const { t } = useLang();
  const { config } = useSite();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const next = safeNext(params.get("next"));
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  if (user) return <Navigate to={next} replace />;
  const done = (u) => {
    setUser(u);
    toast.success(t("login.welcome"));
    navigate(next, { replace: true });
  };
  return (
    <div className="max-w-md mx-auto px-4 py-10 sm:py-16" data-testid="login-page">
      <h1 className="font-serif text-4xl text-stone-900">{t("login.title")}</h1>
      <p className="mt-2 text-stone-600">{t("login.subtitle")}</p>
      <div className="mt-8 bg-white border border-stone-200/80 shadow-sm rounded-2xl p-5 sm:p-7 space-y-5">
        {config?.features?.google_login !== false && (
          <>
            <GoogleButton next={next} />
            <div className="flex items-center gap-3 text-xs uppercase tracking-widest text-stone-500"><span className="h-px flex-1 bg-stone-200" />{t("login.or")}<span className="h-px flex-1 bg-stone-200" /></div>
          </>
        )}
        <Tabs defaultValue="password">
          <TabsList className="grid grid-cols-2 w-full h-auto bg-stone-100 p-1 rounded-xl">
            <TabsTrigger value="password" data-testid="login-tab-password" className="rounded-lg py-2 text-xs sm:text-sm whitespace-normal">{t("login.tab_password")}</TabsTrigger>
            <TabsTrigger value="code" data-testid="login-tab-code" className="rounded-lg py-2 text-xs sm:text-sm whitespace-normal">{t("login.tab_code")}</TabsTrigger>
          </TabsList>
          <TabsContent value="password" className="pt-4"><PasswordLogin onDone={done} /></TabsContent>
          <TabsContent value="code" className="pt-4">
            {sent ? <VerifyCode email={email} onBack={() => setSent(false)} onDone={done} />
              : <RequestCode email={email} setEmail={setEmail} onSent={() => setSent(true)} />}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
