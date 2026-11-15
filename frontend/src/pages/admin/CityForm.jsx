import { useRef, useState } from "react";

function Field({ label, children, hint }) {
  return (
    <label className="flex flex-col gap-1 text-sm font-semibold text-stone-700">
      {label}
      {children}
      {hint && <span className="text-xs font-normal text-stone-500">{hint}</span>}
    </label>
  );
}

function LogoField({ city, isSaved, onUpload, onChange }) {
  const input = useRef(null);
  const [busy, setBusy] = useState(false);
  const pick = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    await onUpload(file);
    setBusy(false);
    e.target.value = "";
  };
  return (
    <div className="flex flex-wrap items-center gap-4 rounded-xl border border-dashed border-stone-300 p-4">
      <img src={city.logoUrl || "/api/static/aol-logo.png"} alt="" className="h-12 w-auto" data-testid="city-logo-preview" />
      <div className="flex flex-wrap gap-2">
        <input ref={input} type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml,image/gif" className="hidden" onChange={pick} data-testid="city-logo-file-input" />
        <button type="button" className="btn-ghost" disabled={!isSaved || busy} onClick={() => input.current.click()} data-testid="city-logo-upload-button">
          {busy ? "Uploading…" : "Upload logo"}
        </button>
        {city.logoUrl && (
          <button type="button" className="btn-ghost" onClick={() => onChange({ logoUrl: undefined })} data-testid="city-logo-reset-button">Use default logo</button>
        )}
      </div>
      <p className="w-full text-xs text-stone-500">{isSaved ? "Uploading saves the logo right away." : "Save the new city first, then upload its logo."}</p>
    </div>
  );
}

export default function CityForm({ city, otherIds, locales, timezones, isSaved, onChange, onRemove, onUpload }) {
  const text = (key) => ({ value: city[key] ?? "", onChange: (e) => onChange({ [key]: e.target.value }) });
  const toggleNearby = (id) => {
    const nearby = city.nearbyCityIds || [];
    onChange({ nearbyCityIds: nearby.includes(id) ? nearby.filter((x) => x !== id) : [...nearby, id] });
  };
  return (
    <div className="grid gap-5 rounded-2xl border border-stone-200 bg-white p-6" data-testid="site-config-form">
      <div className="grid gap-5 sm:grid-cols-2">
        <Field label="City ID" hint="Lowercase, e.g. ottawa"><input className="field" {...text("cityId")} data-testid="city-id-input" /></Field>
        <Field label="Display name"><input className="field" {...text("displayName")} data-testid="city-display-name-input" /></Field>
        <Field label="Time zone">
          <input className="field" list="tz-list" {...text("timezone")} data-testid="city-timezone-input" />
          <datalist id="tz-list">{timezones.map((tz) => <option key={tz} value={tz} />)}</datalist>
        </Field>
        <Field label="Default language">
          <select className="field" {...text("defaultLocale")} data-testid="city-default-locale-select">
            {locales.map((l) => <option key={l} value={l}>{l.toUpperCase()}</option>)}
          </select>
        </Field>
        <Field label="Contact email"><input className="field" type="email" {...text("contactEmail")} data-testid="city-contact-email-input" /></Field>
        <Field label="Contact phone"><input className="field" {...text("contactPhone")} data-testid="city-contact-phone-input" /></Field>
      </div>
      <fieldset className="grid gap-5 rounded-xl bg-stone-50 p-4 sm:grid-cols-4">
        <legend className="px-1 text-sm font-semibold text-stone-700">Course search area</legend>
        <Field label="Latitude" hint="Centre, e.g. 45.4215"><input className="field" inputMode="decimal" {...text("latitude")} data-testid="city-latitude-input" /></Field>
        <Field label="Longitude" hint="e.g. -75.6972"><input className="field" inputMode="decimal" {...text("longitude")} data-testid="city-longitude-input" /></Field>
        <Field label="Radius (km)" hint="Default 50"><input className="field" inputMode="decimal" {...text("radiusKm")} data-testid="city-radius-input" /></Field>
        <Field label="Months ahead" hint="1 to 12, default 2"><input className="field" inputMode="numeric" {...text("monthsAhead")} data-testid="city-months-ahead-input" /></Field>
      </fieldset>
      <Field label="Hosts" hint="One per line, include the port for local addresses (e.g. localhost:5623). www. must be listed to match.">
        <textarea className="field min-h-28 font-mono text-xs" value={(city.hosts || []).join("\n")}
          onChange={(e) => onChange({ hosts: e.target.value.split("\n") })} data-testid="city-hosts-textarea" />
      </Field>
      <fieldset>
        <legend className="text-sm font-semibold text-stone-700">Nearby cities</legend>
        <div className="mt-2 flex flex-wrap gap-3">
          {otherIds.length === 0 && <span className="text-sm text-stone-500">No other cities yet.</span>}
          {otherIds.map((id) => (
            <label key={id} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={(city.nearbyCityIds || []).includes(id)} onChange={() => toggleNearby(id)} data-testid={`city-nearby-${id}`} />
              {id}
            </label>
          ))}
        </div>
      </fieldset>
      <LogoField city={city} isSaved={isSaved} onUpload={onUpload} onChange={onChange} />
      <div>
        <button type="button" className="text-sm font-semibold text-red-700 hover:underline" onClick={onRemove} data-testid="city-remove-button">Remove this city</button>
      </div>
    </div>
  );
}
