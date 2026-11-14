import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowRight, Sparkles } from "lucide-react";
import { useLang } from "../lib/i18n";
import { useSite } from "../lib/site";
import { useAuth } from "../lib/auth";
import { Loading } from "../components/ProtectedRoute";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "../components/ui/accordion";

const fade = (i = 0) => ({ initial: { opacity: 0, y: 18 }, animate: { opacity: 1, y: 0 }, transition: { duration: 0.6, delay: i * 0.1 } });

const Hero = ({ c }) => {
  const { t } = useLang();
  const { user } = useAuth();
  return (
    <section className="relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 pt-10 sm:pt-16 pb-14 grid grid-cols-1 lg:grid-cols-12 gap-10 items-center">
        <div className="lg:col-span-6">
          <motion.p {...fade(0)} className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-[#C24C29] bg-[#FDF2EE] border border-[#F4CDBE] px-3 py-1.5 rounded-full" data-testid="hero-badge">
            <Sparkles size={14} />{c.hero_badge}
          </motion.p>
          <motion.h1 {...fade(1)} className="font-serif text-4xl sm:text-5xl lg:text-6xl leading-[1.05] tracking-tight text-stone-900 mt-5" data-testid="hero-title">{c.hero_title}</motion.h1>
          <motion.p {...fade(2)} className="mt-5 text-base sm:text-lg text-stone-700 leading-relaxed max-w-xl" data-testid="hero-subtitle">{c.hero_subtitle}</motion.p>
          <motion.div {...fade(3)} className="mt-8 flex flex-col sm:flex-row gap-3">
            <Link to="/gifts/new" data-testid="hero-give-gift-cta" className="inline-flex items-center justify-center gap-2 bg-[#D95D39] hover:bg-[#C24C29] text-white font-semibold px-7 py-3.5 rounded-full shadow-sm transition-colors active:scale-[0.98]">
              {c.cta_label}<ArrowRight size={18} />
            </Link>
            <Link to={user ? "/dashboard" : "/login"} data-testid="hero-get-started-cta" className="inline-flex items-center justify-center px-7 py-3.5 rounded-full border border-stone-300 hover:bg-white text-stone-800 font-semibold transition-colors">
              {user ? t("nav.dashboard") : (c.secondary_cta_label || t("landing.signin"))}
            </Link>
          </motion.div>
        </div>
        <motion.div {...fade(2)} className="lg:col-span-6 relative">
          <div className="absolute -inset-4 bg-[#E3A008]/15 rounded-[2.5rem] rotate-2" aria-hidden />
          <img src={c.hero_image} alt="" className="relative w-full h-[300px] sm:h-[420px] object-cover rounded-[2rem] shadow-lg" data-testid="hero-image" />
        </motion.div>
      </div>
    </section>
  );
};

const Steps = ({ c }) => (
  <section id="how" className="bg-white border-y border-stone-200/70">
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-14 sm:py-20">
      <h2 className="font-serif text-3xl sm:text-4xl text-stone-900" data-testid="steps-title">{c.steps_title}</h2>
      <ol className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-8">
        {c.steps.map((s, i) => (
          <li key={i} className="relative pl-14" data-testid={`how-step-${i}`}>
            <span className="absolute left-0 top-0 font-serif text-4xl text-[#D95D39]">{String(i + 1).padStart(2, "0")}</span>
            <h3 className="text-lg font-semibold text-stone-900">{s.title}</h3>
            <p className="mt-2 text-stone-600 leading-relaxed">{s.body}</p>
          </li>
        ))}
      </ol>
    </div>
  </section>
);

const Highlights = ({ c }) => (
  <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 py-14 sm:py-20">
    <h2 className="font-serif text-3xl sm:text-4xl text-stone-900 max-w-2xl" data-testid="highlights-title">{c.highlights_title}</h2>
    <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-6">
      {c.highlights.map((h, i) => (
        <article key={i} data-testid={`program-highlight-card-${i}`} className={`group bg-white rounded-2xl overflow-hidden border border-stone-200/80 shadow-sm hover:shadow-md transition-shadow ${i === 1 ? "md:translate-y-8" : ""}`}>
          {h.image && <img src={h.image} alt="" loading="lazy" className="h-52 w-full object-cover group-hover:scale-[1.03] transition-transform duration-500" />}
          <div className="p-6">
            <h3 className="text-lg font-semibold text-stone-900">{h.title}</h3>
            <p className="mt-2 text-stone-600 leading-relaxed">{h.body}</p>
          </div>
        </article>
      ))}
    </div>
  </section>
);

const Sections = ({ c }) => (
  <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-12 pt-10 pb-6">
    {c.sections.map((s, i) => (
      <div key={i} data-testid={`body-section-${i}`} className="rounded-3xl bg-[#2A4736] text-white p-8 sm:p-12 grid md:grid-cols-12 gap-6 mb-6">
        <h2 className="md:col-span-4 font-serif text-3xl">{s.title}</h2>
        <p className="md:col-span-8 text-[#EBF2ED] text-base sm:text-lg leading-relaxed whitespace-pre-line">{s.body}</p>
      </div>
    ))}
  </section>
);

const Faq = ({ c }) => (
  <section className="max-w-3xl mx-auto px-4 sm:px-6 py-14 sm:py-20">
    <h2 className="font-serif text-3xl sm:text-4xl text-stone-900" data-testid="faq-title">{c.faq_title}</h2>
    <Accordion type="single" collapsible className="mt-8" data-testid="faq-accordion">
      {c.faq.map((f, i) => (
        <AccordionItem key={i} value={`f${i}`} className="border-stone-200">
          <AccordionTrigger data-testid={`faq-item-${i}`} className="text-left text-base font-semibold text-stone-900 hover:no-underline">{f.q}</AccordionTrigger>
          <AccordionContent className="text-stone-700 leading-relaxed text-base">{f.a}</AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  </section>
);

export default function Landing() {
  const { lang } = useLang();
  const { content } = useSite();
  if (!content) return <Loading />;
  const c = content[lang];
  return (
    <div data-testid="landing-page">
      <Hero c={c} />
      <Steps c={c} />
      <Highlights c={c} />
      <Sections c={c} />
      <Faq c={c} />
    </div>
  );
}
