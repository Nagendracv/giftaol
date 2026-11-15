import { useEffect, useRef, useState } from "react";
import { Check, Copy, Info, ShieldCheck } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useSite } from "@/lib/site";
import { fill } from "@/components/SiteLayout";

export const Step = ({ n }) => {
  const { t } = useSite();
  return <p className="mt-6 text-xs font-semibold tracking-[0.14em] text-[#C2512F]" data-testid={`gift-step-${n}`}>{fill(t("giftStep"), { n })}</p>;
};

export const money = (amount, locale) =>
  new Intl.NumberFormat(locale === "fr" ? "fr-CA" : "en-CA", { style: "currency", currency: "CAD", currencyDisplay: "narrowSymbol" }).format(amount);

export const formatDate = (iso, locale) =>
  new Date(iso).toLocaleDateString(locale === "fr" ? "fr-CA" : "en-CA", { year: "numeric", month: "short", day: "numeric" });

const STATUS = {
  active: ["giftStatusActive", "bg-emerald-50 text-emerald-800 border-emerald-200"],
  partly_used: ["giftStatusPartly", "bg-amber-50 text-amber-900 border-amber-200"],
  used_up: ["giftStatusUsedUp", "bg-stone-100 text-stone-700 border-stone-200"],
  revoked: ["giftStatusRevoked", "bg-red-50 text-red-800 border-red-200"],
  locked: ["giftStatusLocked", "bg-red-50 text-red-800 border-red-200"],
};

export function StatusBadge({ status, testId }) {
  const { t } = useSite();
  const [key, cls] = STATUS[status] || STATUS.active;
  return <span className={`inline-flex rounded-full border px-2.5 py-0.5 text-xs font-semibold ${cls}`} data-testid={testId}>{t(key)}</span>;
}

export function Turnstile({ siteKey, onToken }) {
  const el = useRef(null);
  const id = useRef(null);
  useEffect(() => {
    const render = () => {
      if (!el.current || !window.turnstile || id.current !== null) return;
      id.current = window.turnstile.render(el.current, {
        sitekey: siteKey,
        callback: onToken,
        "expired-callback": () => onToken(""),
        "error-callback": () => onToken(""),
      });
    };
    if (window.turnstile) render();
    else {
      let s = document.getElementById("cf-turnstile-js");
      if (!s) {
        s = document.createElement("script");
        s.id = "cf-turnstile-js";
        s.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        s.async = true;
        document.head.appendChild(s);
      }
      s.addEventListener("load", render);
    }
    return () => {
      if (id.current !== null && window.turnstile) window.turnstile.remove(id.current);
      id.current = null;
    };
  }, [siteKey, onToken]);
  return <div ref={el} className="mt-4 min-h-[65px]" data-testid="gift-turnstile" />;
}

export function Notice({ tone = "info", children, testId }) {
  const tones = {
    info: "border-[#F3CFC4] bg-[#FDF3F0] text-stone-800",
    success: "border-emerald-200 bg-emerald-50 text-emerald-900",
    demo: "border-amber-300 bg-amber-50 text-amber-900",
    warn: "border-red-200 bg-red-50 text-red-900",
  };
  const Icon = tone === "success" ? ShieldCheck : Info;
  return (
    <div className={`flex gap-3 rounded-xl border p-4 text-sm leading-relaxed ${tones[tone]}`} data-testid={testId}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function DemoBadge() {
  const { t } = useSite();
  return <span className="rounded-full bg-amber-400 px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider text-amber-950" data-testid="gift-demo-badge">{t("giftDemoBadge")}</span>;
}

export function NextSteps({ testId = "gift-next-steps" }) {
  const { t } = useSite();
  const steps = t("giftNextSteps").split("\n").filter((s) => s.trim());
  return (
    <section data-testid={testId}>
      <h2 className="font-heading text-base font-semibold text-stone-900 md:text-lg">{t("giftNextStepsTitle")}</h2>
      <ol className="mt-3 space-y-2.5">
        {steps.map((s, i) => (
          <li key={i} className="flex gap-3 text-sm text-stone-700">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#D9603B] text-xs font-bold text-white">{i + 1}</span>
            <span className="pt-0.5">{s}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function SecurityNotice() {
  const { t } = useSite();
  return <Notice tone="warn" testId="gift-security-notice"><strong className="block">{t("giftSecurityTitle")}</strong>{t("giftSecurityNotice")}</Notice>;
}

export function CopyCodeButton({ code, testId = "gift-copy-code-button" }) {
  const { t } = useSite();
  const [open, setOpen] = useState(false);
  const [done, setDone] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
    } catch {
      const ta = Object.assign(document.createElement("textarea"), { value: code });
      document.body.appendChild(ta); ta.select(); document.execCommand("copy"); ta.remove();
    }
    setDone(true);
    toast.success(t("giftCopied"));
    setTimeout(() => setDone(false), 2000);
  };
  return (
    <>
      <button type="button" className="btn-ghost" onClick={() => setOpen(true)} data-testid={testId}>
        {done ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}{t("giftCopyCode")}
      </button>
      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent data-testid="gift-security-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>{t("giftSecurityTitle")}</AlertDialogTitle>
            <AlertDialogDescription>{t("giftSecurityNotice")}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="gift-security-cancel">{t("giftCancel")}</AlertDialogCancel>
            <AlertDialogAction onClick={copy} className="bg-[#D9603B] hover:bg-[#C2512F]" data-testid="gift-security-confirm-copy">{t("giftSecurityAgree")}</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
