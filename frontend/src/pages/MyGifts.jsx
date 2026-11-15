import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useClerk } from "@clerk/react";
import { ArrowLeft, Eye, EyeOff, Gift, KeyRound, LogOut, Mail } from "lucide-react";
import { toast } from "sonner";
import { errorText, useAuthedApi } from "@/lib/api";
import { useSite } from "@/lib/site";
import { CopyCodeButton, NextSteps, StatusBadge, formatDate, money } from "@/components/gift/GiftParts";
import { CodeCard } from "@/pages/gift/GiftCheckout";

const mask = (code) => code.replace(/[A-Z0-9]{4}(?=-)/g, "••••");

function useResend(gift, onDone) {
  const call = useAuthedApi();
  const [busy, setBusy] = useState(false);
  const resend = async () => {
    setBusy(true);
    try { toast.success((await call({ url: `/gifts/mine/${gift.id}/resend-email`, method: "post" })).data.message); onDone?.(); }
    catch (e) { toast.error(errorText(e)); }
    setBusy(false);
  };
  return [resend, busy];
}

function Uses({ gift }) {
  const { site, t } = useSite();
  if (!gift.redemptions.length) return <p className="text-sm text-stone-500" data-testid={`gift-no-uses-${gift.id}`}>{t("giftNoUses")}</p>;
  return (
    <ul className="divide-y divide-stone-100 text-sm" data-testid={`gift-uses-${gift.id}`}>
      {gift.redemptions.map((r) => (
        <li key={r.date + r.courseReference} className="flex flex-wrap justify-between gap-2 py-2">
          <span className="font-medium text-stone-800">{r.courseName}</span>
          <span className="text-stone-600">{money(r.amountUsed, site.locale)} · {formatDate(r.date, site.locale)}</span>
        </li>
      ))}
    </ul>
  );
}

function GiftCard({ gift, reload }) {
  const { site, t } = useSite();
  const [shown, setShown] = useState(false);
  const [resend, busy] = useResend(gift, reload);
  return (
    <article className="rounded-2xl border border-stone-200 bg-white p-5" data-testid={`gift-card-${gift.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs text-stone-500">{formatDate(gift.createdAt, site.locale)}{gift.recipientFirstName && ` · ${t("giftRecipient")}: ${gift.recipientFirstName}`}</p>
          <p className="mt-1 font-heading text-xl font-semibold text-stone-900" data-testid={`gift-balance-${gift.id}`}>
            {money(gift.balance, site.locale)} <span className="text-sm font-normal text-stone-500">/ {money(gift.amount, site.locale)} {gift.currency}</span>
          </p>
        </div>
        <StatusBadge status={gift.status} testId={`gift-status-${gift.id}`} />
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <code className="rounded-lg bg-stone-100 px-3 py-1.5 font-mono text-sm tracking-wider" data-testid={`gift-code-${gift.id}`}>{shown ? gift.code : mask(gift.code)}</code>
        <button type="button" className="inline-flex items-center gap-1 text-sm font-semibold text-[#C2512F] hover:underline" onClick={() => setShown(!shown)} data-testid={`gift-reveal-${gift.id}`}>
          {shown ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}{shown ? t("giftHide") : t("giftReveal")}
        </button>
      </div>
      <div className="mt-4"><p className="mb-1 text-xs font-semibold uppercase tracking-wider text-stone-500">{t("giftUses")}</p><Uses gift={gift} /></div>
      <div className="mt-4 flex flex-wrap gap-2">
        <CopyCodeButton code={gift.code} testId={`gift-copy-${gift.id}`} />
        <button type="button" className="btn-ghost" disabled={busy} onClick={resend} data-testid={`gift-resend-email-${gift.id}`}><Mail className="h-4 w-4" />{t("giftResendEmail")}</button>
        <Link to={`/gifts/${gift.id}`} className="btn-ghost" data-testid={`gift-details-${gift.id}`}>{t("giftDetails")}</Link>
      </div>
    </article>
  );
}

export function MyGifts() {
  const { t } = useSite();
  const call = useAuthedApi();
  const [data, setData] = useState(null);
  const load = useCallback(() => { call({ url: "/gifts/mine" }).then((r) => setData(r.data)).catch(() => setData({ gifts: [] })); }, [call]);
  useEffect(load, [load]);
  return (
    <section className="mt-14" data-testid="my-gifts-section">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-heading text-2xl font-semibold text-stone-900">{t("myGiftsTitle")}</h2>
        <Link to="/gift" className="btn-gift" data-testid="new-gift-button"><Gift className="h-4 w-4" />{t("giftNewGift")}</Link>
      </div>
      {data && !data.gifts.length && <p className="mt-4 text-stone-600" data-testid="my-gifts-empty">{t("myGiftsEmpty")}</p>}
      <div className="mt-5 grid gap-4 lg:grid-cols-2">{data?.gifts.map((g) => <GiftCard key={g.id} gift={g} reload={load} />)}</div>
    </section>
  );
}

export function AccountSection({ email }) {
  const { t } = useSite();
  const { openUserProfile, signOut } = useClerk();
  return (
    <section className="mt-14" data-testid="account-section">
      <h2 className="font-heading text-2xl font-semibold text-stone-900">{t("accountTitle")}</h2>
      <div className="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border border-stone-200 bg-white p-5">
        <p className="mr-auto text-sm"><span className="text-stone-500">{t("accountEmail")}: </span><strong data-testid="account-email">{email}</strong></p>
        <button type="button" className="btn-ghost" onClick={() => openUserProfile({ __experimental_startPath: "/security" })} data-testid="account-change-password-button"><KeyRound className="h-4 w-4" />{t("accountManage")}</button>
        <button type="button" className="btn-ghost" onClick={() => signOut({ redirectUrl: "/" })} data-testid="account-logout-button"><LogOut className="h-4 w-4" />{t("accountSignOut")}</button>
      </div>
    </section>
  );
}

export function GiftDetail() {
  const { giftId } = useParams();
  const { site, t } = useSite();
  const call = useAuthedApi();
  const [gift, setGift] = useState(null);
  const [error, setError] = useState("");
  const load = useCallback(() => { call({ url: `/gifts/mine/${giftId}` }).then((r) => setGift(r.data)).catch((e) => setError(errorText(e))); }, [call, giftId]);
  useEffect(load, [load]);
  const [resend, busy] = useResend({ id: giftId }, load);
  return (
    <main className="mx-auto max-w-[760px] px-6 py-12" data-testid="gift-detail-page">
      <Link to="/dashboard" className="inline-flex items-center gap-1 text-sm font-semibold text-[#C2512F]" data-testid="gift-detail-back"><ArrowLeft className="h-4 w-4" />{t("giftBack")}</Link>
      {error && <p className="mt-6 text-red-700" role="alert">{error}</p>}
      {gift && (
        <>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <h1 className="font-display text-4xl text-stone-900 sm:text-5xl">{money(gift.balance, site.locale)} <span className="text-2xl text-stone-500">/ {money(gift.amount, site.locale)}</span></h1>
            <StatusBadge status={gift.status} testId="gift-detail-status" />
          </div>
          {gift.message && <p className="mt-4 whitespace-pre-wrap italic text-stone-700">{gift.message}</p>}
          <CodeCard gift={gift} />
          <button type="button" className="btn-ghost mt-4" disabled={busy} onClick={resend} data-testid="gift-detail-resend-email"><Mail className="h-4 w-4" />{t("giftResendEmail")}</button>
          <section className="mt-8"><h2 className="font-heading text-lg font-semibold">{t("giftUses")}</h2><div className="mt-2"><Uses gift={gift} /></div></section>
          <div className="mt-8"><NextSteps testId="gift-detail-next-steps" /></div>
        </>
      )}
    </main>
  );
}
