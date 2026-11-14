import { useState } from "react";
import { Copy, Eye, EyeOff, ShieldAlert, BadgeCheck } from "lucide-react";
import { toast } from "sonner";
import { useLang } from "../lib/i18n";
import { useSite } from "../lib/site";
import { formatCode } from "../lib/api";

const STATUS_STYLES = {
  active: "bg-green-50 text-green-800 border-green-200",
  partly_used: "bg-amber-50 text-amber-900 border-amber-200",
  used_up: "bg-stone-100 text-stone-700 border-stone-300",
  revoked: "bg-red-50 text-red-800 border-red-200",
};

export const StatusBadge = ({ status, testId = "gift-status-badge" }) => {
  const { t } = useLang();
  return (
    <span data-testid={testId} className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${STATUS_STYLES[status]}`}>
      {t(`status.${status}`)}
    </span>
  );
};

export const PlaceholderBanner = () => {
  const { lang } = useLang();
  const { config } = useSite();
  if (!config) return null;
  return (
    <div data-testid="placeholder-banner" className="flex gap-3 rounded-xl border border-[#2A4736]/30 bg-[#EBF2ED] p-4 text-[#1E3527]">
      <BadgeCheck className="shrink-0 mt-0.5" size={20} />
      <p className="text-sm leading-relaxed font-medium">{config.texts.banner[lang]}</p>
    </div>
  );
};

export const SecurityNotice = () => {
  const { lang, t } = useLang();
  const { config } = useSite();
  if (!config) return null;
  return (
    <div data-testid="security-notice" role="note" className="flex gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-red-900">
      <ShieldAlert className="shrink-0 mt-0.5" size={20} />
      <div>
        <p className="text-sm font-semibold">{t("gift.security_title")}</p>
        <p className="text-sm leading-relaxed mt-0.5">{config.texts.security[lang]}</p>
      </div>
    </div>
  );
};

export const NextSteps = () => {
  const { lang, t } = useLang();
  const { config } = useSite();
  if (!config) return null;
  return (
    <section data-testid="next-steps" aria-labelledby="next-steps-h">
      <h2 id="next-steps-h" className="font-serif text-2xl text-stone-900 mb-4">{t("gift.next")}</h2>
      <ol className="space-y-3">
        {config.texts.next_steps[lang].map((s, i) => (
          <li key={i} className="flex gap-3" data-testid={`next-step-${i}`}>
            <span className="grid place-items-center h-7 w-7 shrink-0 rounded-full bg-[#2A4736] text-white text-sm font-semibold">{i + 1}</span>
            <span className="text-stone-700 leading-relaxed pt-0.5">{s}</span>
          </li>
        ))}
      </ol>
    </section>
  );
};

export const copyText = async (text, msg) => {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement("textarea");
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand("copy");
    ta.remove();
  }
  toast.success(msg);
};

export const MaskedCode = ({ code, prefix = "gift" }) => {
  const [show, setShow] = useState(false);
  const { t } = useLang();
  const full = formatCode(code);
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <code data-testid={`${prefix}-code-value`} className="font-mono font-bold tracking-widest text-amber-950 bg-amber-50 border border-amber-200 px-3 py-1.5 rounded-md text-sm sm:text-base">
        {show ? full : `${full.slice(0, 4)}-••••-••••-••••`}
      </code>
      <button type="button" onClick={() => setShow((s) => !s)} data-testid={`${prefix}-masked-code-reveal-btn`} aria-label={show ? t("common.hide") : t("common.reveal")}
        className="p-2 rounded-lg border border-stone-300 hover:bg-stone-100 text-stone-700">
        {show ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
      <button type="button" onClick={() => copyText(full, t("common.copied"))} data-testid={`${prefix}-code-copy-btn`} aria-label={t("common.copy")}
        className="p-2 rounded-lg border border-stone-300 hover:bg-stone-100 text-stone-700">
        <Copy size={16} />
      </button>
    </div>
  );
};

export const BigCode = ({ code }) => {
  const { t } = useLang();
  const full = formatCode(code);
  return (
    <div className="space-y-4">
      <SecurityNotice />
      <div className="rounded-2xl border border-amber-200 bg-gradient-to-b from-amber-50 to-white p-5 sm:p-7 text-center shadow-inner">
        <p className="text-xs font-semibold uppercase tracking-widest text-amber-800 mb-2">{t("gift.code")}</p>
        <p data-testid="confirmation-gift-code" className="font-mono font-bold text-2xl sm:text-4xl tracking-[0.12em] text-amber-950 break-all">{full}</p>
        <button type="button" data-testid="confirmation-copy-code-btn" onClick={() => copyText(full, t("common.copied"))}
          className="mt-5 inline-flex items-center gap-2 bg-[#D95D39] hover:bg-[#C24C29] text-white font-semibold px-6 py-3 rounded-xl transition-colors active:scale-[0.98]">
          <Copy size={18} />{t("common.copy")}
        </button>
      </div>
    </div>
  );
};
