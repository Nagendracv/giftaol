import { NavLink, Outlet } from "react-router-dom";
import { useMe } from "@/lib/me";
import { useSite } from "@/lib/site";
import { ADMIN_SECTIONS } from "@/pages/Dashboard";

export default function AdminLayout() {
  const { me, error } = useMe();
  const { t } = useSite();
  const note = (cls, text, id) => <p className={`mx-auto max-w-[1200px] px-6 py-10 ${cls}`} data-testid={id}>{text}</p>;
  if (error) return note("text-red-700", error, "admin-error");
  if (!me) return note("text-stone-500", "Loading…", "admin-loading");
  if (me.role !== "admin") return note("text-stone-700", t("notAllowed"), "admin-not-allowed");
  return (
    <div className="mx-auto flex max-w-[1400px] flex-col gap-6 px-4 py-8 md:flex-row md:px-6" data-testid="admin-layout">
      <nav aria-label="Admin" className="md:w-60 md:shrink-0">
        <ul className="flex gap-1 overflow-x-auto md:flex-col">
          {ADMIN_SECTIONS.map(({ to, label, icon: Icon, id }) => (
            <li key={to}>
              <NavLink to={to} data-testid={`admin-nav-${id}`}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive ? "bg-amber-50 text-amber-900" : "text-stone-600 hover:bg-stone-100 hover:text-stone-900"}`}>
                <Icon className="h-4 w-4" aria-hidden="true" />
                {label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <section className="min-w-0 flex-1">
        <Outlet />
      </section>
    </div>
  );
}

export function AdminTitle({ title, children }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <h1 className="font-heading text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
      <div className="flex flex-wrap items-center gap-2">{children}</div>
    </div>
  );
}
