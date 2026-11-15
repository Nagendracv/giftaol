import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { errorText, useAuthedApi } from "@/lib/api";
import { AdminTitle } from "@/pages/admin/AdminLayout";

const num = (v) => (v === "" || v == null ? null : Number(v));

function SettingsForm({ call }) {
  const [form, setForm] = useState(null);
  useEffect(() => {
    call({ url: "/admin/gift-settings" }).then(({ data }) =>
      setForm({ minAmount: String(data.minAmount), maxAmount: data.maxAmount == null ? "" : String(data.maxAmount),
        wrongEntryCap: String(data.wrongEntryCap), presets: data.presets.join(", ") }));
  }, [call]);
  if (!form) return null;
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    try {
      await call({ url: "/admin/gift-settings", method: "put", data: {
        minAmount: num(form.minAmount), maxAmount: num(form.maxAmount), wrongEntryCap: num(form.wrongEntryCap),
        presets: form.presets.split(",").map((p) => Number(p.trim())).filter((p) => p > 0) } });
      toast.success("Gift settings saved");
    } catch (err) { toast.error(errorText(err)); }
  };
  const field = (k, label, hint) => (
    <label className="grid gap-1 text-sm font-medium text-stone-800">{label}
      <input className="field" value={form[k]} onChange={set(k)} data-testid={`gift-settings-${k}`} />
      <span className="text-xs font-normal text-stone-500">{hint}</span>
    </label>
  );
  return (
    <form onSubmit={save} className="grid gap-4 rounded-xl border border-stone-200 bg-white p-5 sm:grid-cols-2 lg:grid-cols-4" data-testid="gift-settings-form">
      {field("minAmount", "Minimum amount (CAD)", "Default 100")}
      {field("maxAmount", "Maximum amount (CAD)", "Blank means no maximum")}
      {field("wrongEntryCap", "Wrong-entry cap", "Locks a code after this many rejected uses")}
      {field("presets", "Quick amounts", "Comma-separated, e.g. 100, 150, 250, 500")}
      <div className="sm:col-span-2 lg:col-span-4 flex items-center justify-between gap-3">
        <p className="text-xs text-stone-500">Page wording (EN/FR) is editable under Text &amp; languages — keys starting with <code>gift</code>.</p>
        <button type="submit" className="btn-primary" data-testid="gift-settings-save">Save settings</button>
      </div>
    </form>
  );
}

function CodesTable({ call }) {
  const [q, setQ] = useState("");
  const [data, setData] = useState(null);
  const load = useCallback(() => {
    call({ url: "/admin/gifts", params: { q: q || undefined } }).then((r) => setData(r.data)).catch((e) => toast.error(errorText(e)));
  }, [call, q]);
  useEffect(load, [load]);
  const act = async (g, action) => {
    try { await call({ url: `/admin/gifts/${g.id}/${action}`, method: "post" }); toast.success(`Code ${action === "unlock" ? "unlocked" : "revoked"}`); load(); }
    catch (e) { toast.error(errorText(e)); }
  };
  return (
    <div className="mt-8">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-heading text-lg font-semibold">Gift codes {data && <span className="text-sm font-normal text-stone-500">({data.total})</span>}</h2>
        <input className="field w-72" placeholder="Search code or giver email" value={q} onChange={(e) => setQ(e.target.value)} data-testid="gift-admin-search" />
      </div>
      <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
        <table className="w-full text-left text-sm" data-testid="gift-admin-table">
          <thead className="bg-stone-100 text-xs uppercase tracking-wider text-stone-700">
            <tr>{["Code", "Giver", "Amount", "Balance", "Status", "Wrong entries", "Uses", "Created", ""].map((h) => <th key={h} className="px-3 py-2.5">{h}</th>)}</tr>
          </thead>
          <tbody>
            {data?.items.map((g) => (
              <tr key={g.id} className="border-b border-stone-100" data-testid="gift-admin-row">
                <td className="px-3 py-2 font-mono">{g.code}</td>
                <td className="px-3 py-2">{g.email}</td>
                <td className="px-3 py-2">{g.amount.toFixed(2)}</td>
                <td className="px-3 py-2">{g.balance.toFixed(2)}</td>
                <td className="px-3 py-2">{g.status}{g.demo && <span className="ml-1 text-xs text-amber-700">(demo)</span>}</td>
                <td className="px-3 py-2">{g.wrongEntries}</td>
                <td className="px-3 py-2">{g.redemptions.length}</td>
                <td className="px-3 py-2">{new Date(g.createdAt).toLocaleDateString()}</td>
                <td className="px-3 py-2 whitespace-nowrap">
                  {g.locked && <button type="button" className="btn-ghost !py-1" onClick={() => act(g, "unlock")} data-testid={`gift-admin-unlock-${g.id}`}>Unlock</button>}
                  {g.rawStatus === "active" && <button type="button" className="ml-2 text-xs font-semibold text-red-700 hover:underline" onClick={() => act(g, "revoke")} data-testid={`gift-admin-revoke-${g.id}`}>Revoke</button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function HarmonyApi() {
  const base = window.location.origin;
  return (
    <div className="mt-8 rounded-xl border border-stone-200 bg-white p-5 text-sm" data-testid="gift-harmony-api">
      <h2 className="font-heading text-lg font-semibold">Harmony API (open for the demo, no key yet)</h2>
      <pre className="mt-3 overflow-x-auto rounded-lg bg-stone-900 p-4 text-xs text-stone-100">{`GET  ${base}/api/gift-codes/{code}
  -> { code, status, balance, amount, currency }   423 = locked, 404 = not found

POST ${base}/api/gift-codes/{code}/redeem
  { "amount": 120.00, "courseName": "Art of Living Part 1", "courseReference": "HARMONY-REG-123" }
  -> { code, status, balance, amountUsed, redemptionId, duplicate }
  409 = over balance / used up / revoked, 423 = locked`}</pre>
    </div>
  );
}

export default function Gifts() {
  const call = useAuthedApi();
  return (
    <div data-testid="gift-admin-page">
      <AdminTitle title="Gifts" />
      <SettingsForm call={call} />
      <CodesTable call={call} />
      <HarmonyApi />
    </div>
  );
}
