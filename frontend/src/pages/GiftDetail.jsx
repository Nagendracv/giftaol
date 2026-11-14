import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { CheckCircle2, ArrowLeft, FlaskConical, MailCheck } from "lucide-react";
import { useLang } from "../lib/i18n";
import { api, errMsg, fmtDate, fmtMoney } from "../lib/api";
import { Loading } from "../components/ProtectedRoute";
import { BigCode, NextSteps, PlaceholderBanner, StatusBadge } from "../components/GiftBits";

const Summary = ({ g }) => {
  const { t, lang } = useLang();
  const rows = [
    [t("dash.original"), fmtMoney(g.amount, lang), "gift-detail-amount"],
    [t("dash.balance"), fmtMoney(g.balance, lang), "gift-detail-balance"],
    [t("gift.date"), fmtDate(g.created_at, lang), "gift-detail-date"],
  ];
  if (g.recipient_first_name) rows.push([t("dash.for"), g.recipient_first_name, "gift-detail-recipient"]);
  const emailLabel = { sent: t("gift.email_sent"), failed: t("gift.email_failed") }[g.email_status] || t("gift.email_pending");
  rows.push([t("gift.email_status"), emailLabel, "gift-detail-email-status"]);
  return (
    <dl className="bg-white border border-stone-200/80 rounded-2xl p-5 divide-y divide-stone-100">
      {rows.map(([k, v, id]) => (
        <div key={id} className="flex justify-between gap-4 py-2.5"><dt className="text-stone-600">{k}</dt><dd className="font-semibold text-right" data-testid={id}>{v}</dd></div>
      ))}
    </dl>
  );
};

const Redemptions = ({ list }) => {
  const { t, lang } = useLang();
  return (
    <section>
      <h2 className="font-serif text-2xl mb-3">{t("gift.uses")}</h2>
      {list.length === 0 ? <p className="text-stone-500" data-testid="gift-detail-no-uses">{t("dash.no_uses")}</p> : (
        <div className="overflow-x-auto bg-white border border-stone-200/80 rounded-2xl">
          <table className="w-full text-sm" data-testid="gift-detail-redemptions">
            <thead className="bg-stone-50 text-left text-stone-600"><tr>
              <th className="p-3 font-medium">{t("gift.course")}</th><th className="p-3 font-medium">{t("gift.used")}</th>
              <th className="p-3 font-medium">{t("gift.after")}</th><th className="p-3 font-medium">{t("gift.date")}</th></tr></thead>
            <tbody>{list.map((r) => (
              <tr key={r.id} className="border-t border-stone-100">
                <td className="p-3">{r.course_name}</td><td className="p-3">{fmtMoney(r.amount_used, lang)}</td>
                <td className="p-3">{fmtMoney(r.balance_after, lang)}</td><td className="p-3 whitespace-nowrap">{fmtDate(r.created_at, lang)}</td></tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </section>
  );
};

export default function GiftDetail() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const isNew = params.get("new") === "1";
  const { t } = useLang();
  const [g, setG] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let timer;
    const load = () => api.get(`/gifts/mine/${id}`).then(({ data }) => {
      setG(data);
      if (data.email_status === "pending") timer = setTimeout(load, 3000);
    }).catch((e) => setError(errMsg(e)));
    load();
    return () => clearTimeout(timer);
  }, [id]);

  const resend = async () => {
    try { await api.post(`/gifts/mine/${id}/resend-email`); toast.success(t("dash.resent")); } catch (e) { toast.error(errMsg(e)); }
  };

  if (error) return <p role="alert" className="max-w-xl mx-auto p-8 text-red-800" data-testid="gift-detail-error">{error}</p>;
  if (!g) return <Loading />;
  return (
    <div className="max-w-3xl mx-auto px-4 py-10 space-y-8" data-testid="gift-detail-page">
      <Link to="/dashboard" className="inline-flex items-center gap-1 text-sm text-[#2A4736] hover:underline" data-testid="gift-detail-back-link"><ArrowLeft size={16} />{t("gift.back")}</Link>
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        {isNew && <CheckCircle2 className="text-green-700 mb-3" size={40} />}
        <h1 className="font-serif text-4xl sm:text-5xl text-stone-900" data-testid="gift-detail-title">{isNew ? t("gift.ready") : t("gift.detail")}</h1>
        {isNew && <p className="text-stone-600 mt-2">{t("gift.ready_sub")}</p>}
        <div className="mt-3 flex gap-2 items-center"><StatusBadge status={g.display_status} /></div>
      </motion.div>
      {g.demo && (
        <p className="flex items-center gap-2 rounded-xl border-2 border-dashed border-amber-400 bg-amber-50 p-4 text-sm font-semibold text-amber-950" data-testid="gift-demo-notice">
          <FlaskConical size={18} />{t("gift.demo_note")}
        </p>
      )}
      <PlaceholderBanner />
      <BigCode code={g.code} />
      <Summary g={g} />
      {g.message && (
        <section><h2 className="font-serif text-2xl mb-2">{t("gift.message")}</h2>
          <blockquote className="border-l-4 border-[#D95D39] bg-[#FDF2EE] p-4 rounded-r-xl whitespace-pre-wrap text-stone-800" data-testid="gift-detail-message">{g.message}</blockquote></section>
      )}
      <NextSteps />
      <Redemptions list={g.redemptions} />
      <button type="button" onClick={resend} data-testid="gift-detail-resend-email-btn" className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl border border-stone-300 hover:bg-white font-medium"><MailCheck size={18} />{t("dash.resend")}</button>
    </div>
  );
}
