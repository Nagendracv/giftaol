// Program search used by both the REST feed and the MCP server.
const norm = (s) => String(s ?? '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');

const TOPIC_SYNONYMS = {
  anxiety: ['anxiety', 'stress'], stress: ['stress', 'anxiety'], sleep: ['sleep'], breathing: ['breathwork'],
  breathwork: ['breathwork'], pranayama: ['breathwork'], meditation: ['meditation'], mindfulness: ['meditation'],
  yoga: ['yoga'], retreat: ['retreat', 'silence'], silent: ['silence', 'retreat'], kids: ['kids'], children: ['kids'],
  teens: ['teens'], students: ['students'], university: ['students'], beginner: ['beginners'], beginners: ['beginners'],
  free: ['free'], volunteer: ['volunteer', 'seva'],
};

export function findPrograms(catalog, { topic, city, level, limit = 5 } = {}) {
  const wanted = topic
    ? [...new Set(norm(topic).split(/[^a-z]+/).flatMap((w) => TOPIC_SYNONYMS[w] ?? []))]
    : [];
  let programs = catalog.programs.map((p) => {
    const hits = wanted.filter((t) => p.topics.includes(t)).length;
    const text = norm(`${p.name} ${p.description}`);
    const textHit = topic ? norm(topic).split(/[^a-z]+/).filter((w) => w.length > 3 && text.includes(w)).length * 0.5 : 0;
    const beginnerBoost = p.level === 'First Steps' ? 0.3 : p.level === 'Entry Level' ? 0.15 : 0;
    const focus = hits / p.topics.length; // prefer programs built for this need over broad ones
    const relevance = hits * 2 + focus * 2 + textHit;
    return { p, relevance, score: relevance + beginnerBoost };
  });
  if (topic) programs = programs.filter((x) => x.relevance > 0);
  if (level) programs = programs.filter((x) => norm(x.p.level) === norm(level));
  programs.sort((a, b) => b.score - a.score);

  const centres = city
    ? catalog.centres.filter((c) => norm(c.city).includes(norm(city)) || norm(city).includes(norm(c.city)))
    : [];
  return {
    query: { topic: topic ?? null, city: city ?? null, level: level ?? null },
    programs: programs.slice(0, limit).map(({ p }) => ({ ...p, provider: catalog.organization.name, findDates: 'https://www.artofliving.org/ca-en/find/course' })),
    centres,
    note: centres.length || !city
      ? 'Programs also run online across Canada.'
      : `No listed centre in ${city} yet. Programs run online across Canada; see https://www.artofliving.org/ca-en/find/course for local dates.`,
  };
}

export const getProgram = (catalog, id) => catalog.programs.find((p) => p.id === id) ?? null;
