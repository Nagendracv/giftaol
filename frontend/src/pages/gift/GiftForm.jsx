import { useCallback, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth, useUser } from "@clerk/react";
import { Sparkles } from "lucide-react";
import { api, errorText, useAuthedApi } from "@/lib/api";
import { useSite } from "@/lib/site";
import { fill } from "@/components/SiteLayout";
import { Notice, Step, Turnstile, money } from "@/components/gift/GiftParts";

export const HERO_IMAGE = "https://images.unsplash.com/photo-1522075782449-e45a34f1ddfb?crop=entropy&cs=srgb&fm=jpg&q=80&w=1400";

export function GiftShell({ children, testId }) {
  return (
    <main className="mx-auto grid max-w-[1200px] gap-10 px-6 py-12 lg:grid-cols-[minmax(0,560px)_1fr] lg:py-16" data-testid={testId}>
      <div className="animate-rise">{children}</div>
      <aside className="hidden lg:block">
        <div className="sticky top-28 overflow-hidden rounded-[28px]">
          <img src={HERO_IMAGE} alt="" className="h-[620px] w-full object-cover" />
        </div>
      </aside>
    </main>
  );
}

export function Eyebrow() {
  const { t } = useSite();
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-[#F3CFC4] bg-white px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-[#C2512F]">
      <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />{t("giftEyebrow")}
    </span>
  );
}

const Label = ({ htmlFor, text, optional }) => {
  const { t } = useSite();
  return <label htmlFor={htmlFor} className="text-sm font-medium text-stone-800">{text}{optional && <span className="ml-1 font-normal text-stone-500">{t("giftOptional")}</span>}</label>;
};

const inputCls = "mt-2 w-full rounded-xl border border-stone-300 bg-white px-4 py-3 text-base shadow-sm transition-colors focus:border-[#D9603B] focus:outline-none";

function AmountField({ config, amount, setAmount }) {
  const { site, t } = useSite();
  return (
    <div>
      <Label htmlFor="gift-amount" text={t("giftAmountLabel")} />
      <div className="mt-2 flex flex-wrap gap-2">
        {config.presets.map((p) => (
          <button key={p} type="button" onClick={() => setAmount(String(p))} data-testid={`gift-amount-preset-${p}`}
            className={`rounded-full border px-4 py-2 text-sm font-semibold transition-colors ${Number(amount) === p ? "border-[#D9603B] bg-[#D9603B] text-white" : "border-stone-300 bg-white text-stone-800 hover:border-[#D9603B]"}`}>
            {money(p, site.locale)}
          </button>
        ))}
      </div>
      <input id="gift-amount" type="number" inputMode="decimal" min={config.minAmount} max={config.maxAmount ?? undefined} step="0.01"
        value={amount} onChange={(e) => setAmount(e.target.value)} className={inputCls} data-testid="gift-amount-input" />
      <p className="mt-1.5 text-xs text-stone-500" data-testid="gift-amount-range">{config.rangeText}</p>
    </div>
  );
}

export const amountOk = (value, config) => {
  const n = Number(value);
  return value !== "" && Number.isFinite(n) && n >= config.minAmount && (config.maxAmount == null || n <= config.maxAmount);
};

export function useGiftConfig() {
  const { site } = useSite();
  const [config, setConfig] = useState(null);
  useEffect(() => { api.get("/gifts/config").then((r) => setConfig(r.data)); }, [site.locale]);
  return config;
}

function GuestEmail({ email, setEmail, siteKey, onToken }) {
  const { t } = useSite();
  return (
    <div className="rounded-2xl border border-stone-200 bg-white p-5">
      <Label htmlFor="gift-email" text={t("giftEmailLabel")} />
      <input id="gift-email" type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} className={inputCls} data-testid="gift-email-input" />
      <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs leading-relaxed text-amber-900" data-testid="gift-email-note">{t("giftEmailNote")}</p>
      <Turnstile siteKey={siteKey} onToken={onToken} />
    </div>
  );
}

export default function GiftForm() {
  const { t } = useSite();
  const { isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();
  const call = useAuthedApi();
  const navigate = useNavigate();
  const config = useGiftConfig();
  const location = useLocation();
  const [form, setForm] = useState(location.state?.draft || { amount: "", message: "", recipientFirstName: "", email: "" });
  const [token, setToken] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const onToken = useCallback((v) => setToken(v), []);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  if (!config || !isLoaded) return null;
  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (!amountOk(form.amount, config)) return setError(fill(t("giftAmountOutOfRange"), { range: config.rangeText }));
    if (!isSignedIn && !token) return setError(t("giftRobotCheck"));
    setBusy(true);
    try {
      const data = { ...form, turnstileToken: token };
      const r = isSignedIn ? await call({ url: "/gifts/checkouts", method: "post", data }) : await api.post("/gifts/checkouts", data);
      navigate(`/gift/${r.data.id}`);
    } catch (err) {
      setError(errorText(err));
      if (!isSignedIn) { window.turnstile?.reset(); setToken(""); }
      setBusy(false);
    }
  };

  return (
    <GiftShell testId="gift-page">
      <Eyebrow />
      <Step n={1} />
      <h1 className="mt-2 font-display text-4xl leading-[1.05] text-stone-900 sm:text-5xl lg:text-6xl" data-testid="gift-title">{t("giftTitle")}</h1>
      <p className="mt-5 text-base text-stone-700 md:text-lg">{t("giftIntro")}</p>
      <form onSubmit={submit} className="mt-8 space-y-6" noValidate data-testid="gift-form">
        <AmountField config={config} amount={form.amount} setAmount={set("amount")} />
        <div>
          <Label htmlFor="gift-message" text={t("giftMessageLabel")} optional />
          <textarea id="gift-message" rows={4} maxLength={config.maxMessage} value={form.message} onChange={(e) => set("message")(e.target.value)}
            className={`${inputCls} resize-y`} data-testid="gift-message-input" />
          <div className="mt-1.5 flex justify-between text-xs text-stone-500"><span>{t("giftMessageHint")}</span><span data-testid="gift-message-count">{form.message.length}/{config.maxMessage}</span></div>
        </div>
        <div>
          <Label htmlFor="gift-recipient" text={t("giftRecipientLabel")} optional />
          <input id="gift-recipient" maxLength={60} value={form.recipientFirstName} onChange={(e) => set("recipientFirstName")(e.target.value)} className={inputCls} data-testid="gift-recipient-input" />
          <p className="mt-1.5 text-xs text-stone-500">{t("giftRecipientHint")}</p>
        </div>
        <Notice testId="gift-how-used"><strong className="block">{t("giftHowUsedTitle")}</strong>{t("giftHowUsedBody")}</Notice>
        {isSignedIn ? (
          <p className="rounded-xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-700" data-testid="gift-signed-in-as">
            {fill(t("giftSignedInAs"), { email: user?.primaryEmailAddress?.emailAddress || "" })}
          </p>
        ) : (
          <GuestEmail email={form.email} setEmail={set("email")} siteKey={config.turnstileSiteKey} onToken={onToken} />
        )}
        {error && <p className="text-sm font-medium text-red-700" role="alert" data-testid="gift-form-error">{error}</p>}
        <button type="submit" disabled={busy} className="btn-gift w-full" data-testid="gift-continue-button">
          {isSignedIn ? t("giftContinuePayment") : t("giftContinueNext")}
        </button>
      </form>
    </GiftShell>
  );
}
