import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useAuthedApi, errorText } from "@/lib/api";
import { AdminTitle } from "@/pages/admin/AdminLayout";

const cellKey = (locale, key) => `${locale}:${key}`;

function TextCell({ data, changes, setChanges, locale, textKey }) {
  const id = cellKey(locale, textKey);
  const override = data.overrides[locale]?.[textKey];
  const value = id in changes ? changes[id] : override ?? data.files[locale]?.[textKey] ?? "";
  return (
    <td className="px-3 py-2 align-top">
      <textarea rows={2} lang={locale} aria-label={`${textKey} (${locale.toUpperCase()})`} value={value}
        onChange={(e) => setChanges({ ...changes, [id]: e.target.value })}
        className={`field w-full ${id in changes ? "border-amber-500" : ""}`} data-testid={`text-input-${locale}-${textKey}`} />
      {override !== undefined && !(id in changes) && <span className="text-xs font-semibold text-amber-800">Edited (file: “{data.files[locale]?.[textKey]}”)</span>}
    </td>
  );
}

export default function Texts() {
  const call = useAuthedApi();
  const [data, setData] = useState(null);
  const [changes, setChanges] = useState({});
  const [error, setError] = useState("");

  useEffect(() => { call({ url: "/admin/texts" }).then((r) => setData(r.data)).catch((e) => setError(errorText(e))); }, [call]);

  const save = async () => {
    const list = Object.entries(changes).map(([id, value]) => {
      const [locale, key] = id.split(/:(.*)/s);
      return { locale, key, value: value.trim() ? value : null };
    });
    try {
      const r = await call({ url: "/admin/texts", method: "put", data: { changes: list } });
      setData(r.data); setChanges({}); setError("");
      toast.success("Texts saved and live");
    } catch (e) { setError(errorText(e)); }
  };

  if (!data) return <p className="text-stone-500">{error || "Loading…"}</p>;
  const dirty = Object.keys(changes).length;
  return (
    <div data-testid="translation-editor-form">
      <AdminTitle title="Text & languages">
        <span className="text-sm text-stone-500" data-testid="translation-dirty-count">{dirty ? `${dirty} unsaved` : "All saved"}</span>
        <button type="button" className="btn-primary" disabled={!dirty} onClick={save} data-testid="save-translations-button">Save texts</button>
      </AdminTitle>
      <p className="mb-4 text-sm text-stone-600">Texts start from the language files. Empty a box to go back to the file text.</p>
      {error && <p className="mb-3 text-sm text-red-700" role="alert">{error}</p>}
      <div className="overflow-x-auto rounded-xl border border-stone-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-100 text-xs uppercase tracking-wider text-stone-700">
            <tr>
              <th scope="col" className="px-3 py-2.5">Key</th>
              {data.locales.map((l) => <th key={l} scope="col" className="px-3 py-2.5">{l === "en" ? "English" : l === "fr" ? "French" : l.toUpperCase()}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.keys.map((k) => (
              <tr key={k} className="border-b border-stone-100">
                <th scope="row" className="px-3 py-2 align-top font-mono text-xs font-medium text-stone-700">{k}</th>
                {data.locales.map((l) => <TextCell key={l} data={data} changes={changes} setChanges={setChanges} locale={l} textKey={k} />)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
