import { Link } from "react-router-dom";
import { useLang } from "../lib/i18n";
import { LEGAL } from "../lib/legal";

export default function Legal({ doc }) {
  const { lang, t } = useLang();
  const d = LEGAL[doc][lang];
  return (
    <article className="max-w-3xl mx-auto px-4 py-10 sm:py-14" data-testid={doc === "privacy" ? "privacy-policy-content" : "terms-of-service-content"}>
      <p className="inline-block text-xs font-bold uppercase tracking-widest bg-amber-100 text-amber-900 px-3 py-1 rounded" data-testid="legal-draft-notice">{t("legal.draft")}</p>
      <h1 className="font-serif text-4xl sm:text-5xl mt-4">{d.title}</h1>
      <p className="text-sm text-stone-500 mt-2">{d.updated}</p>
      <div className="mt-8 space-y-7">
        {d.sections.map(([h, p], i) => (
          <section key={i}>
            <h2 className="text-lg font-semibold text-stone-900">{i + 1}. {h}</h2>
            <p className="mt-2 text-stone-700 leading-relaxed">{p}</p>
          </section>
        ))}
      </div>
    </article>
  );
}

export const NotFound = () => {
  const { t } = useLang();
  return (
    <div className="max-w-xl mx-auto px-4 py-24 text-center" data-testid="not-found-page">
      <h1 className="font-serif text-5xl">{t("notfound.title")}</h1>
      <p className="mt-3 text-stone-600">{t("notfound.body")}</p>
      <Link to="/" className="inline-block mt-6 px-6 py-3 rounded-full bg-[#2A4736] text-white font-semibold" data-testid="not-found-home-link">{t("nav.home")}</Link>
    </div>
  );
};
