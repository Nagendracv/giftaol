import { useEffect, useState } from "react";
import { toast } from "sonner";
import { KeyRound, Copy, Unlock, AlertTriangle } from "lucide-react";
import { api, errMsg, fmtDateTime } from "../../lib/api";
import { useSite } from "../../lib/site";
import { copyText } from "../GiftBits";
import { Loading } from "../ProtectedRoute";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Label } from "../ui/label";
import { Switch } from "../ui/switch";

const Card = ({ title, children, testId }) => (
  <section className="bg-white border border-stone-200 rounded-2xl p-5 sm:p-6 space-y-4" data-testid={testId}>
    <h2 className="font-serif text-2xl">{title}</h2>{children}
  </section>
);

const Num = ({ id, label, value, onChange, hint, testId }) => (
  <div className="space-y-1"><Label htmlFor={id}>{label}</Label>
    <Input id={id} type="number" value={value ?? ""} onChange={(e) => onChange(e.target.value)} className="bg-white" data-testid={testId} />
    {hint && <p className="text-xs text-stone-500">{hint}</p>}</div>
);

const TEXTS = [["explainer", "Discount explainer"], ["banner", "Placeholder banner"], ["security", "Security notice"], ["payment_placeholder", "Payment placeholder text"]];

const HarmonyKey = () => {
  const [info, setInfo] = useState(null);
  const [newKey, setNewKey] = useState("");
  const load = () => api.get("/admin/harmony-key").then(({ data }) => setInfo(data));
  useEffect(() => {
    load();
  }, []);
  const rotate = async () => {
    if (info?.active && !window.confirm("Rotating will stop the current key from working immediately. Continue?")) return;
    const { data } = await api.post("/admin/harmony-key/rotate");
    setNewKey(data.key);
    load();
  };
  const revoke = async () => {
    if (!window.confirm("Revoke the Harmony key? Harmony calls will fail until a new key is created.")) return;
    await api.post("/admin/harmony-key/revoke");
    setNewKey("");
    load();
  };
  if (!info) return <Loading />;
  return (
    <Card title="Harmony API key" testId="admin-harmony-key-section">
      <p className="text-sm text-stone-600">Harmony sends this key in the <code className="font-mono bg-stone-100 px-1">X-Harmony-Key</code> header. Only a hash is stored.</p>
      <p className="text-sm" data-testid="harmony-key-status">{info.active ? <>Active key <code className="font-mono">{info.prefix}…</code> created {fmtDateTime(info.created_at)}</> : "No active key."}</p>
      {newKey && (
        <div className="rounded-xl border-2 border-amber-400 bg-amber-50 p-4 space-y-2" data-testid="harmony-key-shown-once">
          <p className="flex items-center gap-2 font-semibold text-amber-950"><AlertTriangle size={16} />Copy this key now. It will not be shown again.</p>
          <div className="flex gap-2 items-center"><code className="font-mono text-sm break-all flex-1" data-testid="harmony-key-value">{newKey}</code>
            <button type="button" onClick={() => copyText(newKey, "Key copied")} className="p-2 border rounded-lg bg-white" aria-label="Copy key" data-testid="harmony-key-copy-btn"><Copy size={16} /></button></div>
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        <button type="button" onClick={rotate} data-testid="admin-generate-harmony-key-btn" className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#2A4736] text-white text-sm font-semibold"><KeyRound size={16} />{info.active ? "Rotate key" : "Create key"}</button>
        {info.active && <button type="button" onClick={revoke} data-testid="admin-revoke-harmony-key-btn" className="px-4 py-2 rounded-xl border border-red-300 text-red-800 text-sm font-semibold">Revoke key</button>}
      </div>
      <div>
        <p className="text-sm font-semibold mb-2">Recent Harmony calls</p>
        {info.recent_calls.length === 0 ? <p className="text-sm text-stone-500">No calls yet.</p> : (
          <div className="overflow-x-auto"><table className="w-full text-xs" data-testid="harmony-calls-table"><tbody>
            {info.recent_calls.map((c) => (<tr key={c.id} className="border-t border-stone-100">
              <td className="py-1.5 pr-3 whitespace-nowrap">{fmtDateTime(c.ts)}</td><td className="pr-3">{c.endpoint}</td><td className="pr-3 font-mono">{c.code}</td>
              <td className={c.status >= 400 ? "text-red-700 font-semibold" : "text-green-700 font-semibold"}>{c.status}</td></tr>))}
          </tbody></table></div>
        )}
      </div>
    </Card>
  );
};

const LockedCodes = () => {
  const [list, setList] = useState(null);
  const load = () => api.get("/admin/gifts/locked").then(({ data }) => setList(data));
  useEffect(() => {
    load();
  }, []);
  const unlock = async (id) => {
    await api.post(`/admin/gifts/${id}/unlock`);
    toast.success("Code unlocked");
    load();
  };
  return (
    <Card title="Locked codes" testId="admin-locked-codes-section">
      {!list ? <Loading /> : list.length === 0 ? <p className="text-sm text-stone-500" data-testid="no-locked-codes">No locked codes.</p> : (
        <ul className="divide-y divide-stone-100">{list.map((g, i) => (
          <li key={g.id} className="py-2 flex flex-wrap justify-between items-center gap-2" data-testid={`locked-code-${i}`}>
            <span className="font-mono text-sm">{g.code_masked}</span><span className="text-xs text-stone-500">{g.wrong_entries} wrong entries · {fmtDateTime(g.locked_at)}</span>
            <button type="button" onClick={() => unlock(g.id)} data-testid={`unlock-code-btn-${i}`} className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg border border-stone-300 text-sm"><Unlock size={14} />Unlock</button>
          </li>))}</ul>
      )}
    </Card>
  );
};

export const ConfigPanel = () => {
  const { reload } = useSite();
  const [cfg, setCfg] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.get("/admin/config").then(({ data }) => setCfg(data));
  }, []);
  if (!cfg) return <Loading />;
  const set = (k, v) => setCfg({ ...cfg, [k]: v });
  const setText = (k, l, v) => setCfg({ ...cfg, texts: { ...cfg.texts, [k]: { ...cfg.texts[k], [l]: v } } });
  const save = async () => {
    setBusy(true);
    try {
      const body = {
        min_amount: parseFloat(cfg.min_amount), max_amount: cfg.max_amount === "" || cfg.max_amount == null ? null : parseFloat(cfg.max_amount),
        payment_mode: cfg.payment_mode, email_from_name: cfg.email_from_name || "", email_reply_to: cfg.email_reply_to || "",
        code_request_limit: parseInt(cfg.code_request_limit, 10), wrong_entry_cap: parseInt(cfg.wrong_entry_cap, 10),
        features: cfg.features, texts: cfg.texts,
      };
      const { data } = await api.put("/admin/config", body);
      setCfg(data);
      reload();
      toast.success("Configuration saved");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-6" data-testid="admin-config-panel">
      <Card title="Gift amounts" testId="admin-amounts-section">
        <div className="grid sm:grid-cols-2 gap-4">
          <Num id="cfg-min" label="Minimum (CAD)" value={cfg.min_amount} onChange={(v) => set("min_amount", v)} testId="config-min-amount-input" />
          <Num id="cfg-max" label="Maximum (CAD)" value={cfg.max_amount} onChange={(v) => set("max_amount", v)} hint="Leave blank for no maximum." testId="config-max-amount-input" />
        </div>
      </Card>
      <Card title="Payment" testId="admin-payment-section">
        <div className="space-y-1"><Label htmlFor="cfg-mode">Payment mode</Label>
          <select id="cfg-mode" value={cfg.payment_mode} onChange={(e) => set("payment_mode", e.target.value)} className="w-full h-10 rounded-md border border-stone-300 bg-white px-3" data-testid="config-payment-mode-select">
            <option value="placeholder">Placeholder (demo)</option><option value="zeffy">Live — Zeffy (not connected yet)</option><option value="other">Live — other provider (not connected yet)</option>
          </select></div>
        <p className="text-sm rounded-lg bg-stone-50 border p-3" data-testid="config-demo-env-status">
          Demo payments in this deployment: <strong>{cfg.demo_payments_env ? "allowed" : "blocked"}</strong>. This is set by the <code className="font-mono">DEMO_PAYMENTS_ENABLED</code> deployment setting and cannot be changed here.
        </p>
      </Card>
      <Card title="Email sender" testId="admin-email-section">
        <p className="text-sm text-stone-600">The sending address is managed by the email service. You can set the display name and a reply-to inbox.</p>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="space-y-1"><Label htmlFor="cfg-from">Sender name</Label><Input id="cfg-from" value={cfg.email_from_name || ""} placeholder="giftaol.ca" onChange={(e) => set("email_from_name", e.target.value)} data-testid="config-email-from-name-input" /></div>
          <div className="space-y-1"><Label htmlFor="cfg-reply">Reply-to address</Label><Input id="cfg-reply" type="email" value={cfg.email_reply_to || ""} onChange={(e) => set("email_reply_to", e.target.value)} data-testid="config-email-reply-to-input" /></div>
        </div>
      </Card>
      <Card title="Limits" testId="admin-limits-section">
        <div className="grid sm:grid-cols-2 gap-4">
          <Num id="cfg-crl" label="Code requests per email per day" value={cfg.code_request_limit} onChange={(v) => set("code_request_limit", v)} testId="config-code-request-limit-input" />
          <Num id="cfg-wec" label="Wrong entries before a code locks" value={cfg.wrong_entry_cap} onChange={(v) => set("wrong_entry_cap", v)} testId="config-wrong-entry-cap-input" />
        </div>
      </Card>
      <Card title="Texts (EN / FR)" testId="admin-texts-section">
        {TEXTS.map(([k, l]) => (
          <div key={k} className="grid md:grid-cols-2 gap-3">
            {["en", "fr"].map((lang) => (
              <div key={lang} className="space-y-1"><Label>{l} — {lang.toUpperCase()}</Label>
                <Textarea rows={3} value={cfg.texts[k][lang]} onChange={(e) => setText(k, lang, e.target.value)} data-testid={`config-text-${k}-${lang}`} /></div>
            ))}
          </div>
        ))}
        <div className="grid md:grid-cols-2 gap-3">
          {["en", "fr"].map((lang) => (
            <div key={lang} className="space-y-1"><Label>Next steps — {lang.toUpperCase()} (one per line)</Label>
              <Textarea rows={8} value={cfg.texts.next_steps[lang].join("\n")} onChange={(e) => setText("next_steps", lang, e.target.value.split("\n"))}
                onBlur={(e) => setText("next_steps", lang, e.target.value.split("\n").map((s) => s.trim()).filter(Boolean))} data-testid={`config-text-next_steps-${lang}`} /></div>
          ))}
        </div>
      </Card>
      <Card title="Feature switches" testId="admin-features-section">
        {Object.entries(cfg.features).map(([k, v]) => (
          <div key={k} className="flex items-center justify-between"><Label htmlFor={`ft-${k}`}>{k.replace(/_/g, " ")}</Label>
            <Switch id={`ft-${k}`} checked={!!v} onCheckedChange={(val) => set("features", { ...cfg.features, [k]: val })} data-testid={`config-feature-${k}`} /></div>
        ))}
      </Card>
      <button type="button" onClick={save} disabled={busy} data-testid="admin-save-config-btn" className="w-full sm:w-auto px-8 py-3 rounded-xl bg-[#D95D39] hover:bg-[#C24C29] text-white font-semibold disabled:opacity-60">Save configuration</button>
      <LockedCodes />
      <HarmonyKey />
    </div>
  );
};
