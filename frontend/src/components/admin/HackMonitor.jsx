import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { api, fmtDateTime } from "../../lib/api";
import { Input } from "../ui/input";

const statusColor = (s) => (s >= 500 ? "bg-red-100 text-red-900" : s >= 400 ? "bg-amber-100 text-amber-900" : s >= 300 ? "bg-blue-50 text-blue-900" : "bg-green-50 text-green-800");

export const HackMonitor = () => {
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [kind, setKind] = useState("all");
  const [data, setData] = useState(null);
  const load = useCallback(() => {
    api.get("/admin/request-logs", { params: { q, status, kind, limit: 300 } }).then(({ data }) => setData(data));
  }, [q, status, kind]);
  useEffect(() => {
    const id = setTimeout(load, 300);
    return () => clearTimeout(id);
  }, [load]);
  return (
    <div className="space-y-4" data-testid="admin-hack-monitor">
      {data && (
        <div className="grid grid-cols-3 gap-3">
          {[["Requests (30 days)", data.total, "monitor-total"], ["Errors (4xx/5xx)", data.errors, "monitor-errors"], ["Unique IPs", data.unique_ips, "monitor-unique-ips"]].map(([l, v, id]) => (
            <div key={id} className="bg-white border border-stone-200 rounded-xl p-4"><p className="text-xs uppercase tracking-widest text-stone-500">{l}</p><p className="font-serif text-2xl" data-testid={id}>{v}</p></div>
          ))}
        </div>
      )}
      <div className="flex flex-wrap gap-2 items-center">
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search IP, URL, referrer…" className="bg-white max-w-sm" data-testid="admin-hack-monitor-search-input" aria-label="Search logs" />
        <select value={status} onChange={(e) => setStatus(e.target.value)} className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm" data-testid="monitor-status-filter" aria-label="Status filter">
          <option value="all">All statuses</option><option value="2xx">2xx</option><option value="3xx">3xx</option><option value="4xx">4xx</option><option value="5xx">5xx</option>
        </select>
        <select value={kind} onChange={(e) => setKind(e.target.value)} className="h-10 rounded-md border border-stone-300 bg-white px-3 text-sm" data-testid="monitor-kind-filter" aria-label="Type filter">
          <option value="all">Pages and API</option><option value="page">Page visits</option><option value="api">API calls</option>
        </select>
        <button type="button" onClick={load} data-testid="monitor-refresh-btn" className="inline-flex items-center gap-1 h-10 px-4 rounded-md border border-stone-300 bg-white text-sm"><RefreshCw size={14} />Refresh</button>
      </div>
      <div className="overflow-x-auto bg-white border border-stone-200 rounded-2xl">
        <table className="w-full text-xs sm:text-sm" data-testid="admin-hack-monitor-table">
          <thead className="bg-stone-50 text-left text-stone-600"><tr>
            <th className="p-3 font-medium">Time</th><th className="p-3 font-medium">IP address</th><th className="p-3 font-medium">Method</th>
            <th className="p-3 font-medium">URL requested</th><th className="p-3 font-medium">Coming from</th><th className="p-3 font-medium">Status</th></tr></thead>
          <tbody>
            {data?.logs.map((l) => (
              <tr key={l.id} className="border-t border-stone-100 align-top">
                <td className="p-3 whitespace-nowrap">{fmtDateTime(l.ts)}</td>
                <td className="p-3 font-mono whitespace-nowrap">{l.ip}</td>
                <td className="p-3">{l.method}</td>
                <td className="p-3 font-mono break-all max-w-[280px]">{l.path}</td>
                <td className="p-3 break-all max-w-[240px] text-stone-600">{l.referrer || "—"}</td>
                <td className="p-3"><span className={`px-2 py-0.5 rounded font-semibold ${statusColor(l.status)}`}>{l.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
        {data && data.logs.length === 0 && <p className="p-6 text-center text-stone-500">No matching requests.</p>}
      </div>
    </div>
  );
};
