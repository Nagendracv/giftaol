// "How is my event doing?": track a posted event or listing and check whether chatbots now point people to it.
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { DATA } from '../data.js';
import { askClaude } from '../audit/run.js';

const FILE = join(DATA, 'events.json');

export const loadEvents = () => (existsSync(FILE) ? JSON.parse(readFileSync(FILE, 'utf8')) : []);
export const saveEvents = (events) => writeFileSync(FILE, JSON.stringify(events, null, 1));

const slug = (s) => String(s).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40);
const domainOf = (u) => { try { return new URL(u).hostname.toLowerCase(); } catch { return null; } };
const norm = (u) => String(u).replace(/^https?:\/\//, '').replace(/[?#].*$/, '').replace(/\/$/, '').toLowerCase();

export function newEvent(fields) {
  const url = fields.url ? String(fields.url).trim() : '';
  const eventbriteId = fields.eventbriteId || url.match(/eventbrite\.[a-z.]+\/e\/[^?#]*?(\d{9,})/)?.[1] || null;
  return {
    id: `${slug(fields.title || 'event')}-${Date.now().toString(36)}`,
    title: String(fields.title || 'Untitled event').slice(0, 120),
    platform: fields.platform || (url ? domainOf(url) : 'unknown'),
    url, eventbriteId,
    city: fields.city || '', province: fields.province || '', programId: fields.programId || '',
    lang: fields.lang || (fields.province === 'QC' ? 'fr' : 'en'),
    start: fields.start || '', approvedBy: fields.approvedBy || '',
    addedAt: new Date().toISOString(),
    match: { urls: url ? [url] : [], domains: fields.domains ?? [] },
    checks: [], stats: null,
  };
}

// The questions a newcomer in that city might ask, worded like our audit questions.
export function questionsForEvent(event, catalog) {
  const program = catalog.programs.find((p) => p.id === event.programId);
  const topics = program?.topics ?? ['meditation', 'breathwork'];
  const c = event.city || 'Canada';
  const qs = [`meditation classes ${c}`, `breathwork workshop ${c}`];
  if (topics.includes('anxiety') || topics.includes('stress')) qs.push(`breathing course for anxiety ${c}`);
  if (topics.includes('sleep')) qs.push(`meditation for better sleep ${c}`);
  qs.push(`wellness events this weekend ${c}`);
  if (event.lang === 'fr' || event.province === 'QC') qs.push(`cours de méditation ${c}`, `atelier de respiration ${c}`);
  return qs.slice(0, 6).map((query, i) => ({ id: `${event.id}-q${i + 1}`, query, city: c, province: event.province, branded: false }));
}

// Did this answer point at the event? Exact page match first, then the listing's own site.
export function pointsToEvent({ resultUrls = [], resultDomains = [] }, event) {
  const urls = event.match?.urls?.map(norm) ?? [];
  const hitUrl = resultUrls.find((u) => urls.some((m) => norm(u).startsWith(m)) || (event.eventbriteId && u.includes(event.eventbriteId)));
  if (hitUrl) return { found: true, how: 'page', rank: resultUrls.indexOf(hitUrl) + 1 };
  const doms = event.match?.domains ?? [];
  const i = resultDomains.findIndex((d) => doms.includes(d));
  return i >= 0 ? { found: true, how: 'listing site', rank: i + 1 } : { found: false };
}

// Re-read a saved audit run for this event (measured data, no new questions asked).
export function checkFromRun(event, run) {
  const results = run.queries.map((q) => {
    const m = pointsToEvent(q, event);
    return { query: q.query, city: q.city, branded: !!q.branded, found: m.found && q.mentioned, rank: m.found ? m.rank : null };
  });
  return { at: run.runAt, source: 'audit', label: run.label, results };
}

export async function checkEventLive(client, event, catalog) {
  const results = [];
  for (const q of questionsForEvent(event, catalog)) {
    try {
      const r = await askClaude(client, q);
      const m = r.error ? { found: false } : pointsToEvent(r, event);
      results.push({ query: q.query, city: q.city, branded: false, found: m.found, rank: m.rank ?? null, mentioned: !!r.mentioned, error: r.error });
    } catch (e) {
      results.push({ query: q.query, city: q.city, branded: false, found: false, error: e.message });
    }
  }
  return { at: new Date().toISOString(), source: 'live', label: 'REAL', results };
}

const fmtDate = (iso) => new Date(iso).toLocaleDateString('en-CA', { month: 'long', day: 'numeric', year: 'numeric' });

// A plain-language answer to "how is my event doing?"
export function eventReport(event) {
  const last = event.checks.at(-1);
  const lines = [];
  if (!last) {
    lines.push('Not checked yet. Press "Check now" to ask a chatbot the questions a newcomer would ask.');
  } else {
    const hits = last.results.filter((r) => r.found);
    const total = last.results.length;
    lines.push(`On ${fmtDate(last.at)}, chatbots pointed people to it for ${hits.length} of ${total} questions.`);
    if (hits.length) lines.push(`Found for: ${hits.slice(0, 5).map((h) => `"${h.query}"`).join(', ')}${hits.length > 5 ? ` and ${hits.length - 5} more` : ''}.`);
    if (!hits.length) {
      const ageDays = (Date.now() - new Date(event.addedAt)) / 864e5;
      lines.push(ageDays < 14
        ? 'Not found yet. New pages can take a while to show up in search, so check again next week.'
        : 'Still not found. Try posting it on Meetup too, and make sure the title names the city.');
    }
    if (event.checks.length > 1) {
      const prev = event.checks.at(-2).results.filter((r) => r.found).length;
      const d = hits.length - prev;
      lines.push(d > 0 ? `That is ${d} more than the check before.` : d < 0 ? `That is ${-d} fewer than the check before.` : 'No change since the check before.');
    }
  }
  if (event.stats) {
    const s = event.stats;
    lines.push(`Eventbrite: ${s.registered} registered${s.capacity ? ` of ${s.capacity} spots` : ''} (status: ${s.status}). Page views are only in the Eventbrite dashboard.`);
  }
  return lines.join(' ');
}

// Pick the tracked event a free-text question is about ("how is the Sherbrooke workshop doing?").
export function pickEvent(events, question) {
  const words = slug(question).split('-').filter((w) => w.length > 2);
  let best = null, bestScore = 0;
  for (const e of events) {
    const hay = slug(`${e.title} ${e.city} ${e.platform} ${e.programId}`);
    const score = words.filter((w) => hay.includes(w)).length;
    if (score > bestScore) { best = e; bestScore = score; }
  }
  return best ?? events.at(-1) ?? null;
}
