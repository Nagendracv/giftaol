// Share-of-voice scoring for an audit run.
export const OWN_DOMAINS = ['artofliving.org', 'artoflivingcanadacentre.org', 'skycampuscanada.org', 'artofliving.secure.retreat.guru'];

export const isOwn = (domain) => OWN_DOMAINS.some((d) => domain === d || domain.endsWith('.' + d));

// Group noisy hostnames (eventbrite.com.au, eventbrite.ca ...) into one source family.
const FAMILIES = [
  ['eventbrite', 'Eventbrite'], ['meetup.com', 'Meetup'], ['bookretreats.com', 'BookRetreats'],
  ['retreat.guru', 'Retreat Guru'], ['coursetakers.com', 'Coursetakers'], ['poyst.com', 'Poyst directory'],
  ['yellowpages.ca', 'Yellow Pages'], ['shambhala.org', 'Shambhala'], ['srichinmoycentre.org', 'Sri Chinmoy Centre'],
  ['theknowledgeacademy.com', 'The Knowledge Academy'], ['albertahealthservices.ca', 'Alberta Health Services'],
  ['blogto.com', 'blogTO'], ['nowtoronto.com', 'NOW Toronto'], ['straight.com', 'Georgia Straight'],
  ['timeout.com', 'Time Out'], ['montreal.ca', 'Ville de Montréal events'], ['calgary.ca', 'City of Calgary rec'],
  ['happeningnext.com', 'HappeningNext'], ['luma.com', 'Luma'], ['superprof.ca', 'Superprof'], ['apprentus.ca', 'Apprentus'],
  ['othership.us', 'Othership'], ['nobleprog.ca', 'NobleProg'], ['tickettailor.com', 'Ticket Tailor'], ['allevents.in', 'AllEvents'], ['bilginc.com', 'Bilginc'], ['globalnews.ca', 'Global News'], ['utoronto.ca', 'University of Toronto'],
  ['sfu.ca', 'Simon Fraser University'], ['ubc.ca', 'UBC'], ['artofliving.org', 'Art of Living'],
];

export function sourceFamily(domain) {
  const hit = FAMILIES.find(([needle]) => domain.includes(needle));
  return hit ? hit[1] : domain.replace(/^www\./, '');
}

// Kinds of source tell us which lever moves them.
export const SOURCE_KIND = {
  Eventbrite: 'listing', Meetup: 'listing', BookRetreats: 'listing', 'Retreat Guru': 'listing', Coursetakers: 'listing',
  'Poyst directory': 'directory', 'Yellow Pages': 'directory', Superprof: 'listing', Apprentus: 'listing', Luma: 'listing',
  HappeningNext: 'listing', 'Ville de Montréal events': 'civic', 'City of Calgary rec': 'civic',
  blogTO: 'press', 'NOW Toronto': 'press', 'Georgia Straight': 'press', 'Time Out': 'press', 'Global News': 'press',
  'University of Toronto': 'campus', 'Simon Fraser University': 'campus', UBC: 'campus',
  Shambhala: 'competitor', NobleProg: 'competitor', Bilginc: 'competitor', 'Ticket Tailor': 'listing', AllEvents: 'listing', 'Sri Chinmoy Centre': 'competitor', 'The Knowledge Academy': 'competitor', Othership: 'competitor',
};

export function scoreRun(run) {
  const qs = run.queries;
  const unbranded = qs.filter((q) => !q.branded);
  const branded = qs.filter((q) => q.branded);
  const pct = (arr) => (arr.length ? Math.round((100 * arr.filter((q) => q.mentioned).length) / arr.length) : 0);

  const group = (key) => {
    const m = {};
    for (const q of unbranded) {
      m[q[key]] ??= { total: 0, mentioned: 0 };
      m[q[key]].total++;
      if (q.mentioned) m[q[key]].mentioned++;
    }
    return m;
  };

  // How many unbranded queries each source family shows up in (counted once per query).
  const sources = {};
  for (const q of unbranded) {
    const fams = new Set(q.resultDomains.filter((d) => !isOwn(d)).map(sourceFamily));
    for (const f of fams) sources[f] = (sources[f] ?? 0) + 1;
  }
  const topSources = Object.entries(sources)
    .map(([name, queries]) => ({ name, queries, kind: SOURCE_KIND[name] ?? 'other' }))
    .sort((a, b) => b.queries - a.queries || a.name.localeCompare(b.name));

  return {
    runId: run.runId,
    label: run.label,
    shareOfVoice: pct(unbranded),
    brandedRecall: pct(branded),
    unbrandedTotal: unbranded.length,
    unbrandedMentioned: unbranded.filter((q) => q.mentioned).length,
    byCity: group('city'),
    byProvince: group('province'),
    byIntent: group('intent'),
    topSources,
  };
}
