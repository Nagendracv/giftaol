// Listing kit: ready-to-paste copy for the third-party sites AI answers actually cite.
const PLATFORM_RULES = {
  Eventbrite: { titleMax: 75, tagsMax: 10 },
  Meetup: { titleMax: 80, tagsMax: 15 },
  'Retreat Guru': { titleMax: 90, tagsMax: 10 },
  BookRetreats: { titleMax: 90, tagsMax: 10 },
  Coursetakers: { titleMax: 90, tagsMax: 8 },
};

const clip = (s, n) => (s.length <= n ? s : s.slice(0, n - 1).trimEnd() + '…');

export function listingFor({ platform, program, city, catalog }) {
  const rules = PLATFORM_RULES[platform] ?? { titleMax: 80, tagsMax: 10 };
  const where = city ? ` in ${city}` : ' (Online, Canada)';
  const hook = program.topics.includes('anxiety') ? 'Breathwork for Stress & Anxiety' : program.topics.includes('breathwork') ? 'Breathwork & Meditation' : 'Meditation';
  const title = clip(`${hook}${where}: ${program.name}`, rules.titleMax);
  const tags = [...new Set([
    'meditation', 'breathwork', 'breathing techniques', 'stress relief', 'mindfulness',
    ...program.topics, city ? `${city.toLowerCase()} meditation` : 'online meditation', 'art of living', 'SKY breath meditation',
  ])].slice(0, rules.tagsMax);
  const body = [
    `${program.description}`,
    '',
    `Taught by certified teachers from ${catalog.organization.name}, a non-profit that has taught breathing and meditation across Canada for decades.`,
    '',
    `Official program page: ${program.url}`,
    'All dates: https://www.artofliving.org/ca-en/find/course',
  ].join('\n');
  return { platform, title, tags, body, link: program.url };
}

export function listingKit({ catalog, families, cities }) {
  const starters = catalog.programs.filter((p) => ['intro', 'part-1', 'sleep-anxiety'].includes(p.id));
  const retreat = catalog.programs.filter((p) => p.id === 'part-2');
  const out = [];
  for (const platform of families) {
    const isRetreat = platform === 'BookRetreats' || platform === 'Retreat Guru';
    for (const program of isRetreat ? retreat : starters) {
      for (const city of isRetreat ? [null] : cities) out.push(listingFor({ platform, program, city, catalog }));
    }
  }
  return out;
}
