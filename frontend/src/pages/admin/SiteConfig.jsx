import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { toast } from "sonner";
import { useAuthedApi, errorText } from "@/lib/api";
import { AdminTitle } from "@/pages/admin/AdminLayout";
import CityForm from "@/pages/admin/CityForm";

const NEW_CITY = { cityId: "", displayName: "", timezone: "America/Toronto", hosts: [], nearbyCityIds: [], defaultLocale: "en", radiusKm: 50, monthsAhead: 2 };

function clean(config) {
  const cities = config.cities.map((c) => {
    const out = { ...c, hosts: (c.hosts || []).map((h) => h.trim()).filter(Boolean) };
    ["contactEmail", "contactPhone", "logoUrl"].forEach((k) => { if (!out[k]) delete out[k]; });
    ["latitude", "longitude", "radiusKm", "monthsAhead"].forEach((k) => {
      const v = String(out[k] ?? "").trim();
      if (v === "") delete out[k];
      else out[k] = Number.isNaN(Number(v)) ? v : Number(v); // non-numbers go to the server, which explains the error
    });
    return out;
  });
  return { ...config, cities };
}

export default function SiteConfig() {
  const call = useAuthedApi();
  const [payload, setPayload] = useState(null);
  const [draft, setDraft] = useState(null);
  const [selected, setSelected] = useState(0);
  const [timezones, setTimezones] = useState([]);
  const [error, setError] = useState("");

  const apply = (data) => { setPayload(data); setDraft(structuredClone(data.config)); setError(""); };

  useEffect(() => {
    call({ url: "/admin/config" }).then((r) => apply(r.data)).catch((e) => setError(errorText(e)));
    call({ url: "/admin/timezones" }).then((r) => setTimezones(r.data)).catch(() => {});
  }, [call]);

  if (!draft) return <p className="text-stone-500">{error || "Loading…"}</p>;
  const savedIds = payload.config.cities.map((c) => c.cityId);
  const city = draft.cities[selected];

  const updateCity = (patch) => setDraft({ ...draft, cities: draft.cities.map((c, i) => (i === selected ? { ...c, ...patch } : c)) });
  const addCity = () => { setDraft({ ...draft, cities: [...draft.cities, { ...NEW_CITY }] }); setSelected(draft.cities.length); };
  const removeCity = () => { setDraft({ ...draft, cities: draft.cities.filter((_, i) => i !== selected) }); setSelected(0); };

  const run = async (config, message) => {
    try { apply((await call(config)).data); toast.success(message); }
    catch (e) { setError(errorText(e)); }
  };
  const save = () => run({ url: "/admin/config", method: "put", data: clean(draft) }, "Site configuration saved and live");
  const reset = () => window.confirm("Discard admin edits and go back to the configuration file?") &&
    run({ url: "/admin/config", method: "delete" }, "Back to the file configuration");
  const upload = async (file) => {
    const form = new FormData();
    form.append("file", file);
    try {
      const { data } = await call({ url: `/admin/cities/${city.cityId}/logo`, method: "post", data: form });
      setPayload(data);
      updateCity({ logoUrl: data.logoUrl });
      toast.success("Logo uploaded and live");
    } catch (e) { setError(errorText(e)); }
  };

  return (
    <div data-testid="site-config-page">
      <AdminTitle title="Site configuration">
        <span className="rounded-full bg-stone-100 px-3 py-1 text-xs font-semibold text-stone-700" data-testid="site-config-source">
          Source: {payload.source === "admin" ? "saved by admins" : "configuration file"}
        </span>
        {payload.source === "admin" && <button type="button" className="btn-ghost" onClick={reset} data-testid="reset-site-config-button">Reset to file</button>}
        <button type="button" className="btn-primary" onClick={save} data-testid="save-site-config-button">Save changes</button>
      </AdminTitle>
      {error && <pre className="mb-4 whitespace-pre-wrap rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" role="alert" data-testid="site-config-error">{error}</pre>}
      <div className="grid gap-6 lg:grid-cols-[220px_1fr]">
        <ul className="flex flex-col gap-1" data-testid="city-list">
          {draft.cities.map((c, i) => (
            <li key={i}>
              <button type="button" onClick={() => setSelected(i)} data-testid={`city-list-item-${c.cityId || "new"}`}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm transition-colors ${i === selected ? "bg-amber-50 font-semibold text-amber-900" : "hover:bg-stone-100"}`}>
                {c.displayName || "New city"} <span className="block text-xs font-normal text-stone-500">{(c.hosts || []).filter(Boolean).length} hosts</span>
              </button>
            </li>
          ))}
          <li><button type="button" className="btn-ghost mt-2 w-full" onClick={addCity} data-testid="add-city-button"><Plus className="h-4 w-4" aria-hidden="true" />Add city</button></li>
        </ul>
        {city ? (
          <CityForm city={city} otherIds={draft.cities.map((c) => c.cityId).filter((id) => id && id !== city.cityId)}
            locales={payload.locales} timezones={timezones} isSaved={savedIds.includes(city.cityId)}
            onChange={updateCity} onRemove={removeCity} onUpload={upload} />
        ) : <p className="text-stone-500">No cities. Add one to begin.</p>}
      </div>
    </div>
  );
}
