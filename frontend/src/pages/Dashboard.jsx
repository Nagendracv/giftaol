import { Link } from "react-router-dom";
import { BarChart3, Gift, Languages, MapPin, ScrollText, Users } from "lucide-react";
import { useSite } from "@/lib/site";
import { useMe } from "@/lib/me";
import { AccountSection, MyGifts } from "@/pages/MyGifts";

export const ADMIN_SECTIONS = [
  { to: "/admin/logs", label: "Access logs", hint: "Every visit, by site and city", icon: ScrollText, id: "access-logs" },
  { to: "/admin/insights", label: "Visit insights", hint: "Top tabs and courses per site", icon: BarChart3, id: "insights" },
  { to: "/admin/sites", label: "Site configuration", hint: "Cities, hosts and logos", icon: MapPin, id: "site-config" },
  { to: "/admin/texts", label: "Text & languages", hint: "English and French texts", icon: Languages, id: "translations" },
  { to: "/admin/users", label: "Users & admins", hint: "Promote or demote admins", icon: Users, id: "users" },
  { to: "/admin/gifts", label: "Gifts", hint: "Gift limits, codes and unlocks", icon: Gift, id: "gifts" },
];

function AdminMenu() {
  const { t } = useSite();
  return (
    <section className="mt-14" aria-labelledby="admin-menu-title" data-testid="admin-menu">
      <h2 id="admin-menu-title" className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">{t("adminMenu")}</h2>
      <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {ADMIN_SECTIONS.map(({ to, label, hint, icon: Icon, id }) => (
          <Link key={to} to={to} data-testid={`admin-menu-${id}`}
            className="group rounded-2xl border border-stone-200 bg-white p-5 transition-colors hover:border-amber-300 hover:bg-amber-50/40">
            <Icon className="h-5 w-5 text-amber-700" aria-hidden="true" />
            <p className="mt-4 font-heading font-semibold text-stone-900">{label}</p>
            <p className="mt-1 text-sm text-stone-600">{hint}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}

export default function Dashboard() {
  const { site, t } = useSite();
  const { me, error } = useMe();
  return (
    <main className="mx-auto max-w-[1200px] px-6 py-16 sm:py-24" data-testid="user-dashboard">
      <p className="text-sm font-semibold uppercase tracking-[0.18em] text-amber-800" data-testid="dashboard-city">{site.city.displayName}</p>
      <h1 className="font-heading animate-rise mt-3 text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl" data-testid="dashboard-coming-up-title">
        {t("dashboardTitle")}
      </h1>
      <p className="mt-4 max-w-xl text-stone-600" data-testid="dashboard-message">{t("dashboardMessage")}</p>
      {error && <p className="mt-6 text-sm text-red-700" role="alert" data-testid="dashboard-error">{error}</p>}
      <MyGifts />
      {me && <AccountSection email={me.email} />}
      {me?.role === "admin" && <AdminMenu />}
    </main>
  );
}
