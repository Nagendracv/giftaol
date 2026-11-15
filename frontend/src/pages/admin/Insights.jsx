import { useEffect, useState } from "react";
import { useAuthedApi, errorText } from "@/lib/api";
import { AdminTitle } from "@/pages/admin/AdminLayout";

const TAB_LABELS = { newcomer: "Newcomer", advanced: "Advanced", online: "Online" };
const COLUMNS = [
  ["course_open", "Opened"],
  ["register_click", "Register clicks"],
  ["calendar_add", "Calendar adds"],
  ["share", "Shares"],
  ["reminder_signup", "Reminders"],
];

function TabBars({ tabs: found }) {
  const tabs = Object.keys(TAB_LABELS).map((tab) => ({ tab, views: found.find((t) => t.tab === tab)?.views || 0 }));
  const max = Math.max(1, ...tabs.map((t) => t.views));
  return (
    <ul className="grid gap-3" data-testid="insights-tab-views">
      {tabs.map((t) => (
        <li key={t.tab} className="grid grid-cols-[110px_1fr_60px] items-center gap-3 text-sm">
          <span className="font-semibold text-stone-700">{TAB_LABELS[t.tab] || t.tab}</span>
          <span className="h-3 rounded-full bg-stone-100">
            <span className="block h-3 rounded-full bg-amber-600" style={{ width: `${(t.views / max) * 100}%` }} />
          </span>
          <span className="text-right tabular-nums text-stone-700" data-testid={`insights-tab-${t.tab}-views`}>{t.views}</span>
        </li>
      ))}
    </ul>
  );
}

function CourseTable({ courses }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
      <table className="w-full text-left text-sm" data-testid="insights-courses-table">
        <thead className="bg-stone-100 text-xs uppercase tracking-wider text-stone-700">
          <tr>
            <th scope="col" className="px-3 py-2.5">Course</th>
            <th scope="col" className="px-3 py-2.5">City</th>
            {COLUMNS.map(([, label]) => <th key={label} scope="col" className="px-3 py-2.5 text-right">{label}</th>)}
          </tr>
        </thead>
        <tbody>
          {courses.map((c) => (
            <tr key={c.courseId} className="border-b border-stone-100 hover:bg-stone-50" data-testid="insights-course-row">
              <td className="px-3 py-2">
                <span className="font-medium text-stone-900">{c.title}</span>
                <span className="block text-xs text-stone-500">{c.start ? new Date(c.start).toLocaleDateString() : ""} · #{c.courseId}</span>
              </td>
              <td className="px-3 py-2">{c.cityId}</td>
              {COLUMNS.map(([key]) => <td key={key} className="px-3 py-2 text-right tabular-nums">{c[key]}</td>)}
            </tr>
          ))}
          {!courses.length && <tr><td colSpan={7} className="px-3 py-8 text-center text-stone-500">No course activity yet.</td></tr>}
        </tbody>
      </table>
    </div>
  );
}

export default function Insights() {
  const call = useAuthedApi();
  const [cities, setCities] = useState([]);
  const [city, setCity] = useState("");
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    call({ url: "/admin/config" }).then((r) => setCities(r.data.config.cities.map((c) => c.cityId))).catch(() => {});
  }, [call]);
  useEffect(() => {
    setData(null);
    call({ url: "/admin/insights", params: { city: city || undefined, days } })
      .then((r) => { setData(r.data); setError(""); })
      .catch((e) => setError(errorText(e)));
  }, [call, city, days]);

  return (
    <div data-testid="insights-page">
      <AdminTitle title="Visit insights">
        <select className="field" value={city} onChange={(e) => setCity(e.target.value)} aria-label="City" data-testid="insights-city-select">
          <option value="">All cities</option>
          {cities.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select className="field" value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Period" data-testid="insights-days-select">
          {[7, 30, 90].map((d) => <option key={d} value={d}>Last {d} days</option>)}
        </select>
      </AdminTitle>
      {error && <p className="mb-3 text-sm text-red-700" role="alert">{error}</p>}
      {!data && !error && <p className="text-sm text-stone-500" data-testid="insights-loading">Loading…</p>}
      {data && (
        <div className="grid gap-8">
          <section className="rounded-2xl border border-stone-200 bg-white p-6">
            <h2 className="mb-4 font-heading font-semibold">Tab views</h2>
            <TabBars tabs={data.tabs} />
          </section>
          <section>
            <h2 className="mb-3 font-heading font-semibold">Most visited courses</h2>
            <CourseTable courses={data.courses} />
          </section>
        </div>
      )}
    </div>
  );
}
