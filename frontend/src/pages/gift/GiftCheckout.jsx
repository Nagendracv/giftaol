import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useAuth, useSignIn, useUser } from "@clerk/react";
import { CheckCircle2, CreditCard } from "lucide-react";
import { toast } from "sonner";
import { InputOTP, InputOTPGroup, InputOTPSlot } from "@/components/ui/input-otp";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, errorText, useAuthedApi } from "@/lib/api";
import { useSite } from "@/lib/site";
import { fill } from "@/components/SiteLayout";
import { CopyCodeButton, DemoBadge, NextSteps, Notice, SecurityNotice, Step, formatDate, money } from "@/components/gift/GiftParts";
import { Eyebrow, GiftShell, amountOk, useGiftConfig } from "@/pages/gift/GiftForm";

const Title = ({ children, testId }) => (
  <h1 className="mt-2 font-display text-4xl leading-[1.05] text-stone-900 sm:text-5xl" data-testid={testId}>{children}</h1>
);

function useFinishSignIn() {
  const { signIn } = useSignIn();
  return useCallback(async (attempt) => {
    const { error } = await attempt(signIn);
    if (error) throw error;
    if (signIn.status !== "complete") throw new Error("incomplete");
    const done = await signIn.finalize();
    if (done.error) throw done.error;
  }, [signIn]);
}

function CodeTab({ checkout, update }) {
  const { t } = useSite();
  const finish = useFinishSignIn();
  const [code, setCode] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const verify = async () => {
    setBusy(true); setError("");
    try {
      const { data } = await api.post(`/gifts/checkouts/${checkout.id}/verify`, { code });
      if (data.signInTicket) await finish((s) => s.ticket({ ticket: data.signInTicket })).catch(() => {});
      update(data);
    } catch (e) { setError(errorText(e)); }
    setBusy(false);
  };
  return (
    <div className="mt-4">
      <p className="text-sm font-medium text-stone-800">{t("giftCodeLabel")}</p>
      <div className="mt-2 flex flex-wrap items-center gap-3">
        <InputOTP maxLength={6} value={code} onChange={setCode} data-testid="gift-verify-code-input">
          <InputOTPGroup>{[0, 1, 2, 3, 4, 5].map((i) => <InputOTPSlot key={i} index={i} className="h-12 w-11 bg-white text-lg" />)}</InputOTPGroup>
        </InputOTP>
        <button type="button" className="btn-dark" disabled={code.length !== 6 || busy} onClick={verify} data-testid="gift-verify-button">{t("giftVerifyButton")}</button>
      </div>
      {error && <p className="mt-3 text-sm font-medium text-red-700" role="alert" data-testid="gift-verify-error">{error}</p>}
    </div>
  );
}

function PasswordTab({ checkout, update }) {
  const { t } = useSite();
  const finish = useFinishSignIn();
  const call = useAuthedApi();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const signInNow = async (e) => {
    e.preventDefault();
    setBusy(true); setError("");
    try {
      await finish((s) => s.password({ identifier: checkout.email, password }));
    } catch (err) {
      const code = err?.errors?.[0]?.code || err?.code || "";
      setError(code.startsWith("form_password") || code.startsWith("form_identifier") || code === "" ? t("giftPasswordFailed") : errorText(err));
      setBusy(false);
      return;
    }
    try { update((await call({ url: `/gifts/checkouts/${checkout.id}/claim`, method: "post" })).data); }
    catch (err) { setError(errorText(err)); }
    setBusy(false);
  };
  return (
    <form onSubmit={signInNow} className="mt-4" data-testid="gift-password-form">
      <label htmlFor="gift-password" className="text-sm font-medium text-stone-800">{t("giftPasswordLabel")}</label>
      <input id="gift-password" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)}
        className="mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 text-base focus:border-[#D9603B] focus:outline-none" data-testid="gift-password-input" />
      <div id="clerk-captcha" className="mt-3" />
      {error && <p className="mt-3 text-sm font-medium text-red-700" role="alert" data-testid="gift-password-error">{error}</p>}
      <button type="submit" className="btn-dark mt-4" disabled={!password || busy} data-testid="gift-password-sign-in-button">{t("giftSignInButton")}</button>
    </form>
  );
}

function VerifyStep({ checkout, update, onContinue }) {
  const { t } = useSite();
  const { user } = useUser();
  const [error, setError] = useState("");
  const verified = checkout.status === "ready";
  const resend = async () => {
    setError("");
    try { update((await api.post(`/gifts/checkouts/${checkout.id}/resend-code`)).data); toast.success(t("giftCodeResent")); }
    catch (e) { setError(errorText(e)); }
  };
  const accountNote = checkout.hasAccount && (checkout.hasPassword ? t("giftHasAccount") : t("giftHasAccountNoPassword"));
  return (
    <div data-testid="gift-verify-step">
      <Step n={2} />
      <Title testId="gift-verify-title">{t("giftVerifyTitle")}</Title>
      <div className="mt-6 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-5 text-stone-800" data-testid="gift-verify-text">
        <p>{verified ? t("giftVerified") : t("giftVerifyText")} <strong className="break-all" data-testid="gift-verify-sent-to">({checkout.email})</strong></p>
        {!verified && accountNote && <p className="mt-2 text-sm text-stone-600" data-testid="gift-has-account-note">{accountNote}</p>}
        {verified && user && <p className="mt-2 text-sm font-medium text-emerald-800" data-testid="gift-signed-in-now">{fill(t("giftSignedInNow"), { email: user.primaryEmailAddress?.emailAddress || "" })}</p>}
      </div>
      {!verified && (checkout.hasPassword ? (
        <Tabs defaultValue="code" className="mt-6">
          <TabsList className="grid w-full grid-cols-2 rounded-xl bg-stone-100 p-1">
            <TabsTrigger value="code" className="rounded-lg" data-testid="gift-tab-code">{t("giftTabCode")}</TabsTrigger>
            <TabsTrigger value="password" className="rounded-lg" data-testid="gift-tab-password">{t("giftTabPassword")}</TabsTrigger>
          </TabsList>
          <TabsContent value="code"><CodeTab checkout={checkout} update={update} /></TabsContent>
          <TabsContent value="password"><PasswordTab checkout={checkout} update={update} /></TabsContent>
        </Tabs>
      ) : <CodeTab checkout={checkout} update={update} />)}
      {error && <p className="mt-3 text-sm font-medium text-red-700" role="alert" data-testid="gift-resend-error">{error}</p>}
      <button type="button" className="btn-gift mt-8 w-full" disabled={!verified} onClick={onContinue} data-testid="gift-continue-to-payment-button">
        {t("giftContinuePayment")}
      </button>
      {!verified && (
        <p className="mt-5 flex flex-wrap gap-x-2 text-sm text-stone-700">
          <Link to="/gift" state={{ draft: { amount: String(checkout.amount), message: checkout.message, recipientFirstName: checkout.recipientFirstName, email: "" } }}
            className="underline underline-offset-4 hover:text-[#C2512F]" data-testid="gift-change-email-link">{t("giftChangeEmail")}</Link>
          <span aria-hidden="true">·</span>
          <button type="button" className="underline underline-offset-4 hover:text-[#C2512F]" onClick={resend} data-testid="gift-resend-code-button">{t("giftResendCode")}</button>
        </p>
      )}
    </div>
  );
}

function Summary({ checkout }) {
  const { site, t } = useSite();
  const rows = [[t("giftAmount"), money(checkout.amount, site.locale) + " CAD"], [t("giftRecipient"), checkout.recipientFirstName], [t("giftMessage"), checkout.message]];
  return (
    <dl className="mt-6 divide-y divide-stone-100 rounded-2xl border border-stone-200 bg-white px-5" data-testid="gift-summary">
      {rows.filter(([, v]) => v).map(([k, v]) => (
        <div key={k} className="flex gap-4 py-3 text-sm"><dt className="w-32 shrink-0 text-stone-500">{k}</dt><dd className="min-w-0 whitespace-pre-wrap break-words text-stone-900">{v}</dd></div>
      ))}
    </dl>
  );
}

function PayStep({ checkout, update }) {
  const { t } = useSite();
  const config = useGiftConfig();
  const [amount, setAmount] = useState(String(checkout.amount));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  if (!config) return null;
  const pay = async (e) => {
    e.preventDefault();
    if (!amountOk(amount, config)) return setError(fill(t("giftAmountOutOfRange"), { range: config.rangeText }));
    setBusy(true); setError("");
    try { update((await api.post(`/gifts/checkouts/${checkout.id}/pay`, { amount })).data); }
    catch (err) { setError(errorText(err)); setBusy(false); }
  };
  return (
    <div data-testid="gift-pay-step">
      <div className="flex items-center gap-3"><Step n={3} /><span className="mt-6"><DemoBadge /></span></div>
      <Title testId="gift-pay-title">{t("giftPayTitle")}</Title>
      <div className="mt-5"><Notice tone="demo" testId="gift-demo-notice">
        <p className="font-semibold">{t("giftDemoNotice")}</p>
        <p className="mt-1" data-testid="gift-demo-integration-note">{t("giftDemoIntegration")}</p>
        <p className="mt-1" data-testid="gift-demo-pay-hint">{t("giftDemoPayHint")}</p>
      </Notice></div>
      <Summary checkout={checkout} />
      <form onSubmit={pay} className="mt-6 rounded-2xl border-2 border-dashed border-amber-300 bg-white p-5" noValidate>
        <p className="flex items-center gap-2 text-sm font-semibold text-stone-800"><CreditCard className="h-4 w-4" />{t("giftPayAmountLabel")}</p>
        <input type="number" inputMode="decimal" step="0.01" value={amount} onChange={(e) => { setAmount(e.target.value); setError(""); }}
          className="mt-3 w-full rounded-xl border border-stone-300 px-4 py-3 text-base focus:border-[#D9603B] focus:outline-none" data-testid="gift-pay-amount-input" />
        <p className="mt-1.5 text-xs text-stone-500">{config.rangeText}</p>
        {error && <p className="mt-3 text-sm font-medium text-red-700" role="alert" data-testid="gift-pay-error">{error}</p>}
        <button type="submit" disabled={busy} className="btn-gift mt-5 w-full" data-testid="gift-pay-button">{t("giftPayButton")}</button>
      </form>
    </div>
  );
}

export function CodeCard({ gift }) {
  const { site, t } = useSite();
  return (
    <div className="mt-6 rounded-2xl border border-stone-200 bg-white p-6" data-testid="gift-code-card">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-stone-500">{t("giftCode")}</p>
      <p className="mt-2 break-all font-mono text-2xl font-bold tracking-[0.12em] text-stone-900 sm:text-3xl" data-testid="gift-code-value">{gift.code}</p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-stone-500">{t("giftAmount")}</dt><dd className="font-semibold" data-testid="gift-code-amount">{money(gift.amount, site.locale)} {gift.currency}</dd></div>
        <div><dt className="text-stone-500">{t("giftDate")}</dt><dd className="font-semibold">{formatDate(gift.createdAt, site.locale)}</dd></div>
      </dl>
      <div className="mt-5"><SecurityNotice /></div>
      <div className="mt-4"><CopyCodeButton code={gift.code} /></div>
    </div>
  );
}

function ConfirmStep({ checkout }) {
  const { t } = useSite();
  const { isSignedIn } = useAuth();
  const navigate = useNavigate();
  const gift = checkout.gift;
  const toDashboard = () => navigate(isSignedIn ? "/dashboard" : "/sign-in");
  return (
    <div data-testid="gift-confirm-step">
      <div className="mt-6 mb-4 flex items-center gap-3"><CheckCircle2 className="h-6 w-6 text-emerald-600" />{gift.demo && <DemoBadge />}</div>
      <Title testId="gift-confirm-title">{t("giftConfirmTitle")}</Title>
      <div className="mt-5 space-y-3">
        <Notice tone="success" testId="gift-registered-banner"><strong>{t("giftRegisteredBanner")}</strong></Notice>
        {gift.demo && <Notice tone="demo" testId="gift-demo-payment-note">{t("giftDemoPaymentNote")}</Notice>}
      </div>
      <CodeCard gift={gift} />
      <p className="mt-4 text-sm text-stone-600" data-testid="gift-email-status">
        {gift.emailStatus === "failed" ? t("giftEmailFailed") : fill(t("giftEmailSent"), { email: gift.email })}
      </p>
      <div className="mt-8"><NextSteps /></div>
      <div className="mt-8 flex flex-wrap gap-3">
        <button type="button" className="btn-gift" onClick={toDashboard} data-testid="gift-go-dashboard-button">{t("giftViewDashboard")}</button>
        <Link to="/gift" className="btn-ghost" data-testid="gift-new-gift-link">{t("giftNewGift")}</Link>
      </div>
    </div>
  );
}

export default function GiftCheckout() {
  const { checkoutId } = useParams();
  const { site, t } = useSite();
  const [checkout, setCheckout] = useState(null);
  const [missing, setMissing] = useState(false);
  const [paying, setPaying] = useState(false);
  const update = useCallback((c) => setCheckout(c), []);

  useEffect(() => {
    api.get(`/gifts/checkouts/${checkoutId}`).then((r) => setCheckout(r.data)).catch(() => setMissing(true));
  }, [checkoutId, site.locale]);
  useEffect(() => { window.scrollTo(0, 0); }, [checkout?.status, paying]);

  if (missing) return (
    <GiftShell testId="gift-checkout-missing"><p className="text-stone-700">{t("giftNotFound")}</p>
      <Link to="/gift" className="btn-gift mt-6" data-testid="gift-start-over-link">{t("giftStartOver")}</Link></GiftShell>
  );
  if (!checkout) return null;
  const showPay = checkout.status === "ready" && (!checkout.guest || paying);
  return (
    <GiftShell testId="gift-checkout-page">
      <Eyebrow />
      {checkout.status === "paid" ? <ConfirmStep checkout={checkout} />
        : showPay ? <PayStep checkout={checkout} update={update} />
          : <VerifyStep checkout={checkout} update={update} onContinue={() => setPaying(true)} />}
    </GiftShell>
  );
}
