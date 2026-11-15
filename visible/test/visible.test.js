import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import { loadCatalog, listRuns } from '../src/data.js';
import { scoreRun, isOwn } from '../src/score.js';
import { buildPlan, projectShareOfVoice } from '../src/lift/plan.js';
import { parseClaudeResponse } from '../src/audit/run.js';
import { findPrograms } from '../src/feed/search.js';
import { generateAll, cityLandingHtml, faqFor } from '../src/fixes/generate.js';
import { listingKit } from '../src/fixes/listings.js';
import { buildMcpServer } from '../src/feed/mcp.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

const catalog = loadCatalog();
const baseline = listRuns().find((r) => r.runId === 'baseline-2026-11-14');

test('baseline scores match the real audit: 8 of 49 unbranded, 5 of 5 branded', () => {
  const s = scoreRun(baseline);
  assert.equal(s.unbrandedTotal, 49);
  assert.equal(s.unbrandedMentioned, 8);
  assert.equal(s.brandedRecall, 100);
  assert.equal(s.byProvince.ON.total > 0, true);
  assert.equal(s.topSources[0].name, 'Eventbrite');
});

test('own-domain detection includes subdomains but not lookalikes', () => {
  assert.ok(isOwn('www.artofliving.org'));
  assert.ok(isOwn('skycampuscanada.org'));
  assert.ok(!isOwn('notartofliving.org'));
});

test('plan ranks listing sites first and projection grows with more actions', () => {
  const plan = buildPlan(baseline);
  assert.equal(plan.actions[0].family, 'Eventbrite');
  const one = projectShareOfVoice(baseline, plan.actions.slice(0, 1));
  const all = projectShareOfVoice(baseline, plan.actions);
  assert.ok(one > 0 && all > one && all <= 100);
  assert.equal(projectShareOfVoice(baseline, []), scoreRun(baseline).shareOfVoice);
});

test('parses a Claude web-search response into domains, rank and mention', () => {
  const msg = {
    content: [
      { type: 'server_tool_use', id: 's1', name: 'web_search', input: { query: 'x' } },
      { type: 'web_search_tool_result', tool_use_id: 's1', content: [
        { type: 'web_search_result', url: 'https://toronto.shambhala.org/a', title: 'a' },
        { type: 'web_search_result', url: 'https://www.artofliving.org/ca-en/toronto-downtown', title: 'b' },
      ] },
      { type: 'text', text: 'Try the Art of Living Part 1 course.', citations: [{ type: 'web_search_result_location', url: 'https://www.artofliving.org/ca-en/toronto-downtown' }] },
    ],
  };
  const r = parseClaudeResponse(msg);
  assert.deepEqual(r.resultDomains, ['toronto.shambhala.org', 'www.artofliving.org']);
  assert.equal(r.ownRank, 2);
  assert.equal(r.mentioned, true);
  assert.equal(r.citedOwn, true);
  assert.equal(parseClaudeResponse({ content: [{ type: 'text', text: 'Try Shambhala.' }] }).mentioned, false);
});

test('program search maps everyday words to the right programs', () => {
  assert.equal(findPrograms(catalog, { topic: 'help with anxiety' }).programs[0].id, 'sleep-anxiety');
  assert.equal(findPrograms(catalog, { topic: 'university students' }).programs[0].id, 'sky-campus');
  const t = findPrograms(catalog, { topic: 'meditation', city: 'toronto' });
  assert.equal(t.centres.length, 2);
  assert.ok(findPrograms(catalog, { city: 'Sherbrooke' }).centres.length === 1);
  assert.match(findPrograms(catalog, { city: 'Halifax' }).note, /No listed centre in Halifax/);
});

test('fixes produce valid JSON-LD and a page with unique titles', () => {
  const f = generateAll(catalog);
  assert.equal(f.courses.length, catalog.programs.length);
  for (const c of f.courses) assert.equal(c['@type'], 'Course');
  const titles = f.centres.map((c) => c.meta.title);
  assert.equal(new Set(titles).size, titles.length);
  const html = cityLandingHtml({ centre: catalog.centres[0], catalog });
  const blocks = [...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)].map((m) => JSON.parse(m[1]));
  assert.ok(blocks.some((b) => b['@type'] === 'FAQPage'));
  assert.ok(faqFor({ programs: catalog.programs }).items.every((i) => i.status === 'draft-needs-review'));
  assert.match(f.llmsTxt, /Deep Sleep & Anxiety Relief/);
});

test('listing kit respects platform title limits', () => {
  const kit = listingKit({ catalog, families: ['Eventbrite', 'BookRetreats'], cities: ['Toronto'] });
  assert.ok(kit.length >= 4);
  for (const l of kit.filter((k) => k.platform === 'Eventbrite')) assert.ok(l.title.length <= 75);
  assert.ok(kit.some((k) => k.platform === 'BookRetreats' && /Part 2/.test(k.title)));
});

test('MCP server exposes tools and answers find_programs', async () => {
  const server = buildMcpServer(catalog);
  const [a, b] = InMemoryTransport.createLinkedPair();
  await server.connect(a);
  const client = new Client({ name: 't', version: '1' });
  await client.connect(b);
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ['find_programs', 'get_program', 'list_centres']);
  const res = await client.callTool({ name: 'find_programs', arguments: { topic: 'sleep' } });
  assert.equal(JSON.parse(res.content[0].text).programs[0].id, 'sleep-anxiety');
  await client.close();
});

test('French materials cover Québec cities and keep drafts flagged', async () => {
  const { faqFr, listingsFr } = await import('../src/fixes/french.js');
  const f = faqFr({ programs: catalog.programs });
  assert.ok(f.items.length >= 4 && f.items.every((i) => i.status === 'brouillon-a-verifier'));
  assert.equal(f.jsonLd.inLanguage, 'fr-CA');
  const l = listingsFr({ catalog, cities: ['Sherbrooke'] });
  assert.ok(l.every((x) => x.title.length <= 75 && x.body.includes('/ca-fr/')));
});

test('accuracy check sends our fact sheet and returns parsed claims', async () => {
  const { checkAccuracy, factSheet } = await import('../src/audit/accuracy.js');
  assert.match(factSheet(catalog), /Deep Sleep & Anxiety Relief/);
  let sent;
  const fake = { messages: { parse: async (req) => { sent = req; return { stop_reason: 'end_turn', parsed_output: { claims: [{ claim: 'Part 1 costs $5', verdict: 'not_in_our_facts', explanation: 'Prices are not in our facts.' }] } }; } } };
  const out = await checkAccuracy(fake, 'Art of Living Part 1 costs $5.', catalog);
  assert.equal(out.claims[0].verdict, 'not_in_our_facts');
  assert.match(sent.messages[0].content, /<fact_sheet>/);
  assert.ok(sent.output_config.format);
  const refused = await checkAccuracy({ messages: { parse: async () => ({ stop_reason: 'refusal', parsed_output: null }) } }, 'x', catalog);
  assert.deepEqual(refused.claims, []);
});

// ---------- publishing, event tracking, city report cards ----------
import { eventPackages, zonedToUtc, PLATFORMS } from '../src/publish/platforms.js';
import { createDraftEvent, eventStats } from '../src/publish/eventbrite.js';
import { pointsToEvent, checkFromRun, eventReport, newEvent, questionsForEvent, pickEvent } from '../src/events/track.js';
import { cityReport, auditedCities } from '../src/report/city.js';

test('event packages respect platform limits and put Instagram last', () => {
  const cat = loadCatalog();
  const pk = eventPackages(cat, { programId: 'intro', city: 'Calgary', province: 'AB', start: '2026-12-03T19:00' });
  assert.deepEqual(pk.map((p) => p.id), PLATFORMS.map((p) => p.id));
  assert.equal(pk.at(-1).id, 'instagram');
  for (const p of pk) {
    if (p.titleMax) assert.ok(p.title.length <= p.titleMax, p.id);
    if (p.bodyMax) assert.ok(p.body.length <= p.bodyMax, p.id);
  }
  assert.match(pk[0].title, /Calgary/);
  const fr = eventPackages(cat, { programId: 'intro', city: 'Sherbrooke', province: 'QC', lang: 'fr', start: '2026-12-03T19:00' });
  assert.match(fr[0].body, /Inscription/);
});

test('local time converts to UTC across time zones', () => {
  assert.equal(zonedToUtc('2026-12-03T19:00', 'America/Toronto'), '2026-12-04T00:00:00Z');
  assert.equal(zonedToUtc('2026-07-03T19:00', 'America/Vancouver'), '2026-07-04T02:00:00Z');
});

test('Eventbrite: creates a draft with a free ticket, then reads registrations', async () => {
  const calls = [];
  const fake = async (url, opts) => {
    calls.push([opts.method, url.replace('https://www.eventbriteapi.com/v3', ''), opts.body && JSON.parse(opts.body)]);
    const body = url.endsWith('/users/me/organizations/') ? { organizations: [{ id: 'ORG1' }] }
      : url.endsWith('/organizations/ORG1/events/') ? { id: '123456789012', url: 'https://www.eventbrite.ca/e/x-123456789012', status: 'draft' }
      : url.endsWith('/ticket_classes/') && opts.method === 'GET' ? { ticket_classes: [{ quantity_sold: 12, quantity_total: 30 }] }
      : url.endsWith('/events/123456789012/') ? { status: 'live', url: 'u' } : {};
    return { ok: true, json: async () => body };
  };
  const pkg = eventPackages(loadCatalog(), { programId: 'intro', city: 'Calgary', province: 'AB', start: '2026-12-03T19:00' })[0];
  const d = await createDraftEvent({ token: 't', pkg, event: { city: 'Calgary', province: 'AB', start: '2026-12-03T19:00', end: '2026-12-03T20:30', capacity: 30 }, fetchImpl: fake });
  assert.equal(d.id, '123456789012');
  const ev = calls.find((c) => c[1] === '/organizations/ORG1/events/')[2].event;
  assert.equal(ev.start.timezone, 'America/Edmonton');
  assert.equal(ev.start.utc, zonedToUtc('2026-12-03T19:00', 'America/Edmonton')); // follows the tz database (Alberta's rules can change)
  assert.ok(!('status' in ev), 'never sets the event live');
  assert.ok(calls.some((c) => c[1] === '/events/123456789012/ticket_classes/' && c[2].ticket_class.free));
  assert.ok(!calls.some((c) => c[1].includes('/publish')), 'never publishes');
  const s = await eventStats({ token: 't', eventId: '123456789012', fetchImpl: fake });
  assert.equal(s.registered, 12); assert.equal(s.capacity, 30);
});

test('event tracking: matches the event page, explains the result, picks the right event', () => {
  const cat = loadCatalog();
  const ev = newEvent({ title: 'Breath intro Calgary', url: 'https://www.eventbrite.ca/e/breath-intro-calgary-123456789012', city: 'Calgary', province: 'AB', programId: 'intro' });
  assert.equal(ev.eventbriteId, '123456789012');
  assert.ok(pointsToEvent({ resultUrls: ['https://x.com', 'https://www.eventbrite.ca/e/breath-intro-calgary-123456789012?aff=a'] }, ev).found);
  assert.equal(pointsToEvent({ resultUrls: ['https://www.eventbrite.ca/e/other-999999999999'] }, ev).found, false);
  assert.ok(questionsForEvent(ev, cat).every((q) => q.query.includes('Calgary')));
  ev.checks.push({ at: new Date().toISOString(), label: 'REAL', results: [{ query: 'meditation classes Calgary', found: true }, { query: 'breathwork workshop Calgary', found: false }] });
  assert.match(eventReport(ev), /1 of 2 questions/);
  const other = newEvent({ title: 'Sherbrooke atelier', city: 'Sherbrooke' });
  assert.equal(pickEvent([ev, other], 'how is the sherbrooke one doing'), other);
});

test('worked example: Retreat Guru listing is found in the real audit', () => {
  const run = listRuns()[0];
  const ex = JSON.parse(readFileSync(new URL('../data/events.json', import.meta.url))).find((e) => e.fromAudit);
  const c = checkFromRun(ex, run);
  const hits = c.results.filter((r) => r.found).map((r) => r.query);
  assert.ok(hits.includes('retraite de méditation Mauricie'));
  assert.ok(!hits.includes('breathing course for anxiety Toronto'), 'another centre on Retreat Guru does not count');
});

test('city report card narrows the audit to one city with a to-do list', () => {
  const run = listRuns()[0];
  assert.equal(auditedCities(run).length, 31);
  const r = cityReport({ city: 'Calgary', run, catalog: loadCatalog() });
  assert.equal(r.everydayFound, 0);
  assert.ok(r.todo.length >= 2);
  assert.ok(r.todo.some((t) => t.listing && /Calgary/.test(t.listing.title)));
  assert.ok(r.todo.some((t) => /centre page/.test(t.title)), 'no Calgary centre, so ask for one');
  const m = cityReport({ city: 'Markham', run, catalog: loadCatalog() });
  assert.equal(m.everydayFound, 1);
});
