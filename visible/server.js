// Visible: AI-search visibility kit for Art of Living Canada.
import { createServer } from 'node:http';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';
import { ROOT, loadCatalog, loadSiteFacts, loadQueries, listRuns, saveRun } from './src/data.js';
import { scoreRun, isOwn, sourceFamily } from './src/score.js';
import { buildPlan, projectionCurve, ASSUMPTIONS } from './src/lift/plan.js';
import { generateAll, cityLandingHtml, llmsTxt } from './src/fixes/generate.js';
import { listingKit } from './src/fixes/listings.js';
import { faqFr, listingsFr } from './src/fixes/french.js';
import { findPrograms, getProgram } from './src/feed/search.js';
import { buildMcpServer } from './src/feed/mcp.js';
import Anthropic from '@anthropic-ai/sdk';
import { runAudit, askClaude } from './src/audit/run.js';
import { checkAccuracy } from './src/audit/accuracy.js';
import { eventPackages, PLATFORMS } from './src/publish/platforms.js';
import { createDraftEvent, eventStats } from './src/publish/eventbrite.js';
import { loadEvents, saveEvents, newEvent, checkFromRun, checkEventLive, eventReport, questionsForEvent } from './src/events/track.js';
import { auditedCities, cityReport, cityReportHtml, citySlug } from './src/report/city.js';

const PORT = Number(process.env.PORT ?? 3000);
const catalog = loadCatalog();
const auditJob = { running: false, done: 0, total: 0, current: null, error: null, lastRunId: null };

const hasAiKey = () => !!(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN);

// Events with their latest plain-language report. Worked examples are re-read from the newest audit run.
export function eventsWithReports(runs = listRuns()) {
  const latest = runs.at(-1);
  return loadEvents().map((e) => {
    const ev = e.fromAudit && latest ? { ...e, checks: [checkFromRun(e, latest)] } : e;
    return { ...ev, questions: questionsForEvent(ev, catalog).map((q) => q.query), report: eventReport(ev) };
  });
}

const send = (res, status, body, type = 'application/json; charset=utf-8') => {
  res.writeHead(status, { 'content-type': type, 'access-control-allow-origin': '*' });
  res.end(typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body, null, 2));
};

const readBody = (req) => new Promise((resolve, reject) => {
  let data = '';
  req.on('data', (c) => { data += c; if (data.length > 1e6) req.destroy(); });
  req.on('end', () => { try { resolve(data ? JSON.parse(data) : undefined); } catch (e) { reject(e); } });
  req.on('error', reject);
});

export function state() {
  const runs = listRuns();
  const baseline = runs[0];
  const plan = buildPlan(baseline);
  const cities = [...new Set(catalog.centres.map((c) => c.city))].filter((c) => c !== 'Saint-Mathieu-du-Parc');
  const families = [...new Set(plan.actions.filter((a) => a.lever === 'listing').slice(0, 5).map((a) => a.family))];
  return {
    runs: runs.map((r) => ({ ...scoreRun(r), runAt: r.runAt, method: r.method, queries: r.queries.map((q) => ({ ...q, sources: [...new Set(q.resultDomains.filter((d) => !isOwn(d)).map(sourceFamily))] })) })),
    siteFacts: loadSiteFacts(),
    plan,
    projection: projectionCurve(baseline, plan),
    assumptions: ASSUMPTIONS,
    fixes: generateAll(catalog),
    listings: [...listingKit({ catalog, families, cities }), ...listingsFr({ catalog, cities: ['Montréal', 'Québec', 'Sherbrooke'] })],
    faqFr: faqFr({ programs: catalog.programs }),
    catalog,
    auditJob,
    liveAuditAvailable: hasAiKey(),
    publishAvailable: { eventbrite: !!process.env.EVENTBRITE_TOKEN },
    platforms: PLATFORMS,
    events: eventsWithReports(runs),
    cities: auditedCities(runs.at(-1)).map((city) => {
      const r = cityReport({ city, run: runs.at(-1), catalog });
      return { city, slug: r.slug, province: r.province, found: r.everydayFound, total: r.everydayTotal };
    }),
  };
}

async function startAudit() {
  if (auditJob.running) return;
  const { queries } = loadQueries();
  Object.assign(auditJob, { running: true, done: 0, total: queries.length, error: null });
  try {
    const run = await runAudit({ queries, onProgress: (i, n, q) => Object.assign(auditJob, { done: i, current: q }) });
    saveRun(run);
    auditJob.lastRunId = run.runId;
  } catch (e) {
    auditJob.error = e.message;
  } finally {
    auditJob.running = false;
  }
}

export async function handler(req, res) {
  const url = new URL(req.url, `http://${req.headers.host ?? 'localhost'}`);
  const path = url.pathname;
  try {
    if (req.method === 'OPTIONS') {
      res.writeHead(204, { 'access-control-allow-origin': '*', 'access-control-allow-headers': '*', 'access-control-allow-methods': 'GET,POST,DELETE' });
      return res.end();
    }
    if (path === '/mcp') {
      // Stateless MCP over Streamable HTTP: a fresh server per request.
      const mcp = buildMcpServer(catalog);
      const transport = new StreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
      res.on('close', () => { transport.close(); mcp.close(); });
      await mcp.connect(transport);
      const body = req.method === 'POST' ? await readBody(req) : undefined;
      return transport.handleRequest(req, res, body);
    }
    if (path === '/' || path === '/index.html') return send(res, 200, readFileSync(join(ROOT, 'public/index.html')), 'text/html; charset=utf-8');
    if (path === '/platforms.js') return send(res, 200, readFileSync(join(ROOT, 'src/publish/platforms.js')), 'text/javascript; charset=utf-8');
    if (path === '/api/state') return send(res, 200, state());
    if (path === '/api/programs') {
      return send(res, 200, findPrograms(catalog, {
        topic: url.searchParams.get('topic') ?? undefined, city: url.searchParams.get('city') ?? undefined,
        level: url.searchParams.get('level') ?? undefined,
      }));
    }
    if (path.startsWith('/api/programs/')) {
      const p = getProgram(catalog, decodeURIComponent(path.split('/').pop()));
      return p ? send(res, 200, p) : send(res, 404, { error: 'not found' });
    }
    if (path === '/feed.json') {
      const f = generateAll(catalog);
      return send(res, 200, { '@context': 'https://schema.org', '@graph': [f.organization, ...f.courses, ...f.centres.map((c) => c.jsonLd)] });
    }
    if (path === '/llms.txt') return send(res, 200, llmsTxt(catalog), 'text/plain; charset=utf-8');
    const m = path.match(/^\/fixes\/city\/([a-z0-9-]+)\.html$/);
    if (m) {
      const centre = catalog.centres.find((c) => c.id === m[1]);
      return centre ? send(res, 200, cityLandingHtml({ centre, catalog }), 'text/html; charset=utf-8') : send(res, 404, 'not found', 'text/plain');
    }
    const rep = path.match(/^\/report\/([a-z0-9-]+)\.html$/);
    if (rep) {
      const run = listRuns().at(-1);
      const city = auditedCities(run).find((c) => citySlug(c) === rep[1]);
      if (!city) return send(res, 404, 'not found', 'text/plain');
      const events = eventsWithReports();
      return send(res, 200, cityReportHtml(cityReport({ city, run, catalog, events })), 'text/html; charset=utf-8');
    }
    if (path === '/api/publish/preview' && req.method === 'POST') {
      const body = (await readBody(req)) ?? {};
      return send(res, 200, eventPackages(catalog, body.event ?? {}));
    }
    if (path === '/api/publish/eventbrite' && req.method === 'POST') {
      if (!process.env.EVENTBRITE_TOKEN) return send(res, 400, { error: 'Posting to Eventbrite needs the centre\'s Eventbrite private token (EVENTBRITE_TOKEN) on the server.' });
      const body = (await readBody(req)) ?? {};
      const approvedBy = String(body.approvedBy ?? '').trim().slice(0, 80);
      if (!approvedBy || body.checked !== true) return send(res, 400, { error: 'A volunteer has to review the listing, tick the box and add their name first.' });
      const event = body.event ?? {};
      if (!event.start || !event.city) return send(res, 400, { error: 'Add the city, date and start time first.' });
      const pkg = { ...eventPackages(catalog, event).find((p) => p.id === 'eventbrite'), ...(body.pkg ?? {}) };
      const draft = await createDraftEvent({ token: process.env.EVENTBRITE_TOKEN, pkg, event });
      const tracked = newEvent({ ...event, title: pkg.title, url: draft.url, eventbriteId: draft.id, platform: 'Eventbrite', approvedBy });
      saveEvents([...loadEvents(), tracked]);
      return send(res, 201, { draft, tracked });
    }
    if (path === '/api/events' && req.method === 'POST') {
      const body = (await readBody(req)) ?? {};
      if (!body.title && !body.url) return send(res, 400, { error: 'Add the event name or its link.' });
      const ev = newEvent(body);
      saveEvents([...loadEvents(), ev]);
      return send(res, 201, ev);
    }
    const chk = path.match(/^\/api\/events\/([a-z0-9-]+)\/check$/);
    if (chk && req.method === 'POST') {
      const events = loadEvents();
      const ev = events.find((e) => e.id === chk[1]);
      if (!ev) return send(res, 404, { error: 'not found' });
      if (!hasAiKey() && !(ev.eventbriteId && process.env.EVENTBRITE_TOKEN)) return send(res, 400, { error: 'Checking needs an AI account key (ANTHROPIC_API_KEY) on the server.' });
      if (hasAiKey()) ev.checks.push(await checkEventLive(new Anthropic(), ev, catalog));
      if (ev.eventbriteId && process.env.EVENTBRITE_TOKEN) {
        try { ev.stats = await eventStats({ token: process.env.EVENTBRITE_TOKEN, eventId: ev.eventbriteId }); } catch (e) { ev.statsError = e.message; }
      }
      saveEvents(events);
      return send(res, 200, { ...ev, report: eventReport(ev) });
    }
    if (path === '/api/audit/run' && req.method === 'POST') {
      if (!hasAiKey()) {
        return send(res, 400, { error: 'Live re-test needs ANTHROPIC_API_KEY set on the server.' });
      }
      startAudit();
      return send(res, 202, auditJob);
    }
    if (path === '/api/audit/status') return send(res, 200, auditJob);
    if (path === '/api/ask' && req.method === 'POST') {
      if (!(process.env.ANTHROPIC_API_KEY || process.env.ANTHROPIC_AUTH_TOKEN)) {
        return send(res, 400, { error: 'Asking a chatbot live needs ANTHROPIC_API_KEY set on the server.' });
      }
      const body = (await readBody(req)) ?? {};
      const question = String(body.question ?? '').trim().slice(0, 300);
      if (!question) return send(res, 400, { error: 'Type a question first.' });
      const client = new Anthropic();
      const r = await askClaude(client, { query: question, city: String(body.city ?? '').slice(0, 60) || undefined });
      if (r.error) return send(res, 502, r);
      const accuracy = r.mentioned ? await checkAccuracy(client, r.answer, catalog) : null;
      return send(res, 200, { question, ...r, sources: [...new Set(r.resultDomains.filter((d) => !isOwn(d)).map(sourceFamily))], accuracy });
    }
    return send(res, 404, { error: 'not found' });
  } catch (e) {
    console.error(e);
    if (!res.headersSent) send(res, 500, { error: e.message });
  }
}

export const server = createServer(handler);

if (process.argv[1] && import.meta.url.endsWith(process.argv[1].split('/').pop())) {
  server.listen(PORT, () => console.log(`Visible running on http://localhost:${PORT}`));
}
