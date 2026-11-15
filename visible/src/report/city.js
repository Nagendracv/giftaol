// City report card: one page a local centre coordinator can read, print or forward.
// It narrows the national audit to one city: what people there asked, who got sent where, and what to do this week.
import { isOwn, sourceFamily, SOURCE_KIND } from '../score.js';
import { listingFor } from '../fixes/listings.js';

export const citySlug = (c) => String(c).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

const ALIAS = { 'North Vancouver': 'Vancouver', 'Québec City': 'Québec', Quebec: 'Québec', Mauricie: 'Saint-Mathieu-du-Parc' };

export function auditedCities(run) {
  return [...new Set(run.queries.filter((q) => q.city && q.city !== 'Canada').map((q) => q.city))].sort((a, b) => a.localeCompare(b));
}

export function cityReport({ city, run, catalog, events = [] }) {
  const qs = run.queries.filter((q) => q.city === city);
  const everyday = qs.filter((q) => !q.branded);
  const found = everyday.filter((q) => q.mentioned);
  const province = qs[0]?.province ?? '';
  const fr = province === 'QC';
  const centreCity = ALIAS[city] ?? city;
  const centres = catalog.centres.filter((c) => c.city === centreCity || c.city === city || c.area === city);

  const winners = {};
  for (const q of everyday) for (const f of new Set(q.resultDomains.filter((d) => !isOwn(d)).map(sourceFamily))) winners[f] = (winners[f] ?? 0) + 1;
  const topSources = Object.entries(winners).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([name, n]) => ({ name, n, kind: SOURCE_KIND[name] ?? 'other' }));

  const intro = catalog.programs.find((p) => p.id === 'intro') ?? catalog.programs[0];
  const todo = [];
  for (const s of topSources.filter((s) => s.kind === 'listing' && s.name !== 'Retreat Guru').slice(0, 2)) {
    todo.push({
      title: `Post the next intro session in ${city} on ${s.name}`,
      why: `${s.name} came up for ${s.n} of the ${everyday.length} questions people in ${city} asked.`,
      who: 'Any volunteer', time: 'About 30 minutes',
      listing: listingFor({ platform: s.name, program: intro, city, catalog }),
    });
  }
  if (!centres.length) {
    todo.push({ title: `Ask the website team for a ${city} centre page`, why: 'Where we have a centre page (Markham, Richmond Hill, Kitchener-Waterloo, Sherbrooke), we came up. There is none for this city.', who: 'Centre coordinator', time: 'One email' });
  } else if (!found.length) {
    todo.push({ title: `Check that the ${centres[0].name} page names the city in its title`, why: 'There is a centre page, but it did not come up for these questions.', who: 'Website team', time: 'About 15 minutes' });
  }
  if (fr) todo.push({ title: 'Post in French too', why: 'Many people here search in French. French listings and answers are ready in "Ready-made materials".', who: 'Any volunteer', time: 'About 20 minutes' });

  return {
    city, slug: citySlug(city), province, fr, centres,
    questions: qs.map((q) => ({ query: q.query, branded: !!q.branded, mentioned: !!q.mentioned, note: q.note ?? null, sources: [...new Set(q.resultDomains.filter((d) => !isOwn(d)).map(sourceFamily))].slice(0, 4) })),
    everydayTotal: everyday.length, everydayFound: found.length,
    topSources, todo,
    events: events.filter((e) => e.city === city || e.city === centreCity),
    runAt: run.runAt, label: run.label,
  };
}

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);

export function cityReportHtml(r) {
  const date = new Date(r.runAt).toLocaleDateString('en-CA', { year: 'numeric', month: 'long', day: 'numeric' });
  return `<!doctype html>
<html lang="en-CA"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(r.city)} report card · Visible</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Plus+Jakarta+Sans:wght@500;600;700&display=swap" rel="stylesheet">
<style>
:root{--ink:#1C1917;--muted:#78716C;--line:#E7E5E4;--bg:#FAF9F6;--panel:#fff;--accent:#B45309;--good:#16A34A;--bad:#DC2626}
:root{color-scheme:light}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 "DM Sans",-apple-system,"Segoe UI",sans-serif}
h1,h2,.score{font-family:"Plus Jakarta Sans",-apple-system,sans-serif;letter-spacing:-.02em}
th{background:#F5F5F4;text-transform:uppercase;letter-spacing:.08em;font-size:11.5px}
main{max-width:820px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:28px;margin:0 0 4px}h2{font-size:19px;margin:28px 0 8px}
.muted{color:var(--muted)}.small{font-size:14px}
.score{font-size:44px;font-weight:700;line-height:1.1}.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:20px 22px;margin:12px 0}
table{width:100%;border-collapse:collapse;font-size:15px}td,th{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}th{color:var(--muted);font-size:13px}
.yes{color:var(--good);font-weight:600}.no{color:var(--bad);font-weight:600}
pre{white-space:pre-wrap;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:10px;font-size:13px}
.tag{display:inline-block;font-size:12px;font-weight:600;padding:2px 8px;border-radius:99px;background:#e3f2e8;color:#2f7d4f}
a{color:var(--accent)}
@media print{body{background:#fff}.noprint{display:none}}
</style></head><body><main>
<p class="small muted noprint"><a href="../index.html">← Back to Visible</a> · <a href="#" onclick="print();return false">Print this page</a></p>
<h1>${esc(r.city)}: can newcomers find us?</h1>
<p class="muted">Report card for the local centre team. From the check on ${esc(date)} <span class="tag">Measured</span></p>
<div class="card"><div class="score">${r.everydayFound} of ${r.everydayTotal}</div>
<p style="margin:4px 0 0">everyday questions about ${esc(r.city)} led to Art of Living.${r.centres.length ? ` Centre${r.centres.length > 1 ? 's' : ''} here: ${r.centres.map((c) => `<a href="${esc(c.url)}">${esc(c.name)}</a>`).join(', ')}.` : ' We have no centre page for this city yet.'}</p></div>
<h2>What people asked</h2>
<div class="card"><table><tr><th>Question</th><th>Did we come up?</th><th>Where they were sent</th></tr>
${r.questions.map((q) => `<tr><td>${esc(q.query)}${q.branded ? ' <span class="muted small">(names us)</span>' : ''}${q.note ? `<br><span class="small muted">${esc(q.note)}</span>` : ''}</td><td class="${q.mentioned ? 'yes' : 'no'}">${q.mentioned ? 'Yes' : 'No'}</td><td class="small">${esc(q.sources.join(', ') || '-')}</td></tr>`).join('')}
</table></div>
<h2>This week's to-do list</h2>
${r.todo.map((t, i) => `<div class="card"><b>${i + 1}. ${esc(t.title)}</b><br><span class="small muted">${esc(t.who)} · ${esc(t.time)}</span><p style="margin:6px 0 0">${esc(t.why)}</p>${t.listing ? `<details><summary class="small">Ready-to-paste text</summary><pre>${esc(`${t.listing.title}\n\n${t.listing.body}\n\nTags: ${t.listing.tags.join(', ')}`)}</pre></details>` : ''}</div>`).join('')}
${r.events.length ? `<h2>Events we're tracking here</h2>${r.events.map((e) => `<div class="card"><b>${esc(e.title)}</b><p class="small" style="margin:4px 0 0">${esc(e.report ?? '')}</p></div>`).join('')}` : ''}
<p class="small muted">Made with Visible. The questions were asked the way a chatbot searches the web from Canada. Re-checking after the to-do list is done shows whether it worked.</p>
</main></body></html>
`;
}
