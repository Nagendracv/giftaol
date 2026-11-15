import { useCallback, useEffect, useState } from "react";
import { useAuthedApi, errorText } from "@/lib/api";
import { AdminTitle } from "@/pages/admin/AdminLayout";

const SIZE = 25;

function Filters({ cities, city, setCity, host, setHost }) {
  return (
    <div className="mb-4 flex flex-wrap gap-3">
      <label className="flex flex-col text-xs font-semibold text-stone-600">
        City
        <select value={city} onChange={(e) => setCity(e.target.value)} className="field mt-1 min-w-44" data-testid="filter-city-select">
          <option value="">All cities</option>
          {cities.map((c) => <option key={c} value={c}>{c}</option>)}
          <option value="unknown">unknown</option>
        </select>
      </label>
      <label className="flex flex-col text-xs font-semibold text-stone-600">
        Host contains
        <input value={host} onChange={(e) => setHost(e.target.value)} placeholder="e.g. aolottawa.ca" className="field mt-1 min-w-56" data-testid="filter-host-input" />
      </label>
    </div>
  );
}

function LogRow({ row }) {
  return (
    <tr className="border-b border-stone-100 hover:bg-stone-50" data-testid="access-log-row">
      <td className="whitespace-nowrap px-3 py-2">{new Date(row.ts).toLocaleString()}</td>
      <td className="px-3 py-2 font-mono text-xs">{row.ip}</td>
      <td className="px-3 py-2">{row.host || "—"}</td>
      <td className="max-w-[260px] truncate px-3 py-2 font-mono text-xs" title={row.path}>{row.path}</td>
      <td className="px-3 py-2">
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${row.city_id === "unknown" ? "bg-red-50 text-red-800" : "bg-amber-50 text-amber-900"}`}>{row.city_id}</span>
      </td>
      <td className="px-3 py-2">{row.status}</td>
    </tr>
  );
}

export default function AccessLogs() {
  const call = useAuthedApi();
  const [cities, setCities] = useState([]);
  const [city, setCity] = useState("");
  const [host, setHost] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ items: [], total: 0 });
  const [error, setError] = useState("");

  useEffect(() => {
    call({ url: "/admin/config" }).then((r) => setCities(r.data.config.cities.map((c) => c.cityId))).catch(() => {});
  }, [call]);

  const load = useCallback(() => {
    call({ url: "/admin/logs", params: { city: city || undefined, host: host || undefined, page, size: SIZE } })
      .then((r) => { setData(r.data); setError(""); })
      .catch((e) => setError(errorText(e)));
  }, [call, city, host, page]);

  useEffect(() => { const id = setTimeout(load, 250); return () => clearTimeout(id); }, [load]);
  useEffect(() => setPage(1), [city, host]);

  const pages = Math.max(1, Math.ceil(data.total / SIZE));
  return (
    <div data-testid="access-logs-page">
      <AdminTitle title="Access logs">
        <span className="text-sm text-stone-500" data-testid="access-logs-total">{data.total} visits · kept 90 days</span>
      </AdminTitle>
      <Filters cities={cities} city={city} setCity={setCity} host={host} setHost={setHost} />
      {error && <p className="mb-3 text-sm text-red-700" role="alert">{error}</p>}
      <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
        <table className="w-full text-left text-sm" data-testid="access-logs-table">
          <thead className="bg-stone-100 text-xs uppercase tracking-wider text-stone-700">
            <tr>{["Time", "IP", "Host", "Path", "City", "Status"].map((h) => <th key={h} scope="col" className="px-3 py-2.5 font-semibold">{h}</th>)}</tr>
          </thead>
          <tbody>
            {data.items.map((row) => <LogRow key={row.id} row={row} />)}
            {!data.items.length && <tr><td colSpan={6} className="px-3 py-8 text-center text-stone-500">No visits match.</td></tr>}
          </tbody>
        </table>
      </div>
      <div className="mt-4 flex items-center justify-end gap-3 text-sm">
        <button type="button" className="btn-ghost" disabled={page <= 1} onClick={() => setPage(page - 1)} data-testid="pagination-prev-button">Previous</button>
        <span data-testid="pagination-status">Page {page} of {pages}</span>
        <button type="button" className="btn-ghost" disabled={page >= pages} onClick={() => setPage(page + 1)} data-testid="pagination-next-button">Next</button>
      </div>
    </div>
  );
}
