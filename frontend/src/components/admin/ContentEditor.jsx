import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Plus, Trash2, Undo2 } from "lucide-react";
import { api, errMsg, fmtDateTime } from "../../lib/api";
import { useSite } from "../../lib/site";
import { Loading } from "../ProtectedRoute";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Label } from "../ui/label";

const SIMPLE = [
  ["hero_badge", "Hero badge", "text"], ["hero_title", "Hero title", "text"], ["hero_subtitle", "Hero subtitle", "textarea"],
  ["hero_image", "Hero image", "image"], ["cta_label", "Main button label (Give a gift)", "text"],
  ["secondary_cta_label", "Second button label (Get started)", "text"],
  ["steps_title", "How-it-works title", "text"], ["highlights_title", "Program highlights title", "text"],
  ["faq_title", "FAQ title", "text"], ["footer_text", "Footer text", "textarea"], ["contact_email", "Contact email", "text"],
];
const LISTS = [
  ["steps", "How-it-works steps", [["title", "Title", "text"], ["body", "Text", "textarea"]]],
  ["highlights", "Program highlights", [["title", "Title", "text"], ["body", "Text", "textarea"], ["image", "Image", "image"]]],
  ["sections", "Body sections", [["title", "Title", "text"], ["body", "Text", "textarea"]]],
  ["faq", "FAQ", [["q", "Question", "text"], ["a", "Answer", "textarea"]]],
];

const ImageField = ({ value, onChange, testId }) => {
  const upload = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 800 * 1024) return toast.error("Image is too large. Please use an image under 800 KB, or paste a URL.");
    const r = new FileReader();
    r.onload = () => onChange(r.result);
    r.readAsDataURL(f);
  };
  return (
    <div className="space-y-2">
      <Input value={value?.startsWith("data:") ? "(uploaded image)" : value || ""} onChange={(e) => onChange(e.target.value)} placeholder="https://…" className="bg-white" data-testid={`${testId}-url`} />
      <div className="flex items-center gap-3 min-w-0">
        <label className="cursor-pointer inline-flex items-center px-3 py-1.5 rounded-lg border border-stone-300 bg-white hover:bg-stone-50 text-sm font-medium">
          Upload image
          <input type="file" accept="image/*" onChange={upload} className="sr-only" data-testid={`${testId}-upload`} />
        </label>
        {value && <img src={value} alt="" className="h-12 w-20 shrink-0 object-cover rounded border" />}
      </div>
    </div>
  );
};

const FieldInput = ({ type, value, onChange, testId }) => {
  if (type === "image") return <ImageField value={value} onChange={onChange} testId={testId} />;
  if (type === "textarea") return <Textarea rows={3} value={value || ""} onChange={(e) => onChange(e.target.value)} className="bg-white" data-testid={testId} />;
  return <Input value={value || ""} onChange={(e) => onChange(e.target.value)} className="bg-white" data-testid={testId} />;
};

const ListEditor = ({ name, label, fields, items, setItems }) => {
  const update = (i, k, v) => setItems(items.map((it, j) => (j === i ? { ...it, [k]: v } : it)));
  return (
    <fieldset className="border border-stone-200 rounded-xl p-3 sm:p-4 space-y-4 min-w-0">
      <legend className="px-2 font-semibold text-stone-900">{label}</legend>
      {items.map((it, i) => (
        <div key={i} className="bg-stone-50 rounded-lg p-3 space-y-2" data-testid={`content-${name}-item-${i}`}>
          {fields.map(([k, l, type]) => (
            <div key={k} className="space-y-1"><Label className="text-xs">{l}</Label>
              <FieldInput type={type} value={it[k]} onChange={(v) => update(i, k, v)} testId={`content-${name}-${i}-${k}`} /></div>
          ))}
          <button type="button" onClick={() => setItems(items.filter((_, j) => j !== i))} data-testid={`content-${name}-remove-${i}`} className="inline-flex items-center gap-1 text-sm text-red-700 hover:underline"><Trash2 size={14} />Remove</button>
        </div>
      ))}
      <button type="button" onClick={() => setItems([...items, Object.fromEntries(fields.map(([k]) => [k, ""]))])} data-testid={`content-${name}-add`} className="inline-flex items-center gap-1 text-sm font-medium text-[#2A4736] hover:underline"><Plus size={14} />Add item</button>
    </fieldset>
  );
};

export const ContentEditor = () => {
  const { reload } = useSite();
  const [data, setData] = useState(null);
  const [loc, setLoc] = useState("en");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    api.get("/admin/content").then(({ data }) => setData(data));
  }, []);
  if (!data) return <Loading />;
  const c = data[loc];
  const set = (k, v) => setData({ ...data, [loc]: { ...c, [k]: v } });
  const save = async () => {
    setBusy(true);
    try {
      const { data: d } = await api.put("/admin/content", { en: data.en, fr: data.fr });
      setData(d);
      reload();
      toast.success("Landing page published");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const rollback = async () => {
    try {
      const { data: d } = await api.post("/admin/content/rollback");
      setData(d);
      reload();
      toast.success("Previous version restored");
    } catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="space-y-6 min-w-0 max-w-full overflow-x-hidden" data-testid="admin-content-editor">
      <div className="flex flex-wrap items-center justify-between gap-3 sticky top-16 z-10 bg-[#FAF7F2]/95 backdrop-blur py-3">
        <div className="flex rounded-full border border-stone-300 p-0.5 bg-white" role="group" aria-label="Content language" data-testid="admin-en-fr-toggle">
          {["en", "fr"].map((l) => (
            <button key={l} type="button" onClick={() => setLoc(l)} aria-pressed={loc === l} data-testid={`admin-content-locale-${l}`}
              className={`px-4 py-1.5 text-sm font-semibold rounded-full ${loc === l ? "bg-[#2A4736] text-white" : "text-stone-700"}`}>{l === "en" ? "English" : "Français"}</button>
          ))}
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={rollback} disabled={!data.versions} data-testid="admin-rollback-content-btn" className="inline-flex items-center gap-1 px-4 py-2 rounded-xl border border-stone-300 bg-white disabled:opacity-50 text-sm font-medium"><Undo2 size={16} />Restore previous</button>
          <button type="button" onClick={save} disabled={busy} data-testid="admin-save-content-btn" className="px-5 py-2 rounded-xl bg-[#D95D39] hover:bg-[#C24C29] text-white text-sm font-semibold disabled:opacity-60">Save and publish</button>
        </div>
      </div>
      {data.updated_at && <p className="text-xs text-stone-500">Last published {fmtDateTime(data.updated_at)} by {data.updated_by}</p>}
      <div className="grid gap-4 bg-white border border-stone-200 rounded-2xl p-5">
        {SIMPLE.map(([k, l, type]) => (
          <div key={k} className="space-y-1"><Label className="text-sm">{l}</Label>
            <FieldInput type={type} value={c[k]} onChange={(v) => set(k, v)} testId={`content-field-${k}`} /></div>
        ))}
      </div>
      {LISTS.map(([k, l, fields]) => <ListEditor key={k} name={k} label={l} fields={fields} items={c[k] || []} setItems={(v) => set(k, v)} />)}
    </div>
  );
};
