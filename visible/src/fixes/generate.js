// Turns the real program catalog into the fixes AI engines read: JSON-LD, FAQ content, llms.txt, page metadata.
const ORG_ID = 'https://www.artofliving.org/ca-en#org';

export function organizationJsonLd(org) {
  return {
    '@context': 'https://schema.org',
    '@type': ['Organization', 'NGO'],
    '@id': ORG_ID,
    name: org.name,
    url: org.url,
    telephone: org.phone,
    address: { '@type': 'PostalAddress', ...org.address },
    sameAs: org.sameAs,
    areaServed: { '@type': 'Country', name: 'Canada' },
  };
}

export function courseJsonLd(p) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Course',
    '@id': `${p.url}#course`,
    name: p.name,
    description: p.description,
    url: p.url,
    provider: { '@id': ORG_ID },
    educationalLevel: p.level,
    keywords: p.topics.join(', '),
    inLanguage: ['en-CA', 'fr-CA'],
    availableLanguage: ['English', 'French'],
    // Course instances need real dates and prices from the registration system before going live.
  };
}

export function centreJsonLd(c) {
  return {
    '@context': 'https://schema.org',
    '@type': ['LocalBusiness', 'HealthAndBeautyBusiness'],
    '@id': `${c.url}#place`,
    name: c.name,
    url: c.url,
    parentOrganization: { '@id': ORG_ID },
    address: { '@type': 'PostalAddress', addressLocality: c.city, addressRegion: c.region, addressCountry: 'CA' },
    knowsAbout: ['meditation', 'breathwork', 'SKY Breath Meditation', 'stress relief', 'yoga'],
  };
}

// Question templates mirror the unbranded queries from the audit, so each answers a real gap.
const FAQ_TEMPLATES = [
  {
    intents: ['learn meditation', 'learn meditation (FR)'],
    q: (city) => `Where can I learn meditation in ${city}?`,
    a: (city, ps) => `The Art of Living Foundation teaches meditation in ${city} and online across Canada. Beginners usually start with ${ps('part-1')} or the ${ps('intro')}; ${ps('sahaj')} teaches a mantra-based practice.`,
  },
  {
    intents: ['breathwork'],
    q: (city) => `Are there breathwork classes in ${city}?`,
    a: (city, ps) => `Yes. ${ps('part-1')} teaches SKY Breath Meditation (Sudarshan Kriya), a rhythmic breathing technique, in ${city} and online. Graduates join weekly ${ps('follow-ups')} to practise together.`,
  },
  {
    intents: ['anxiety', 'stress'],
    q: () => 'Is there a breathing course for anxiety or stress in Canada?',
    a: (city, ps) => `${ps('sleep-anxiety')} is a short program of breathing and relaxation practices for anxiety and sleep. ${ps('part-1')} goes deeper with SKY Breath Meditation, and SKY has been studied in peer-reviewed research on stress and anxiety.`,
  },
  {
    intents: ['sleep'],
    q: () => 'Is there a breathing program to help me sleep better?',
    a: (city, ps) => `${ps('sleep-anxiety')} teaches breathing and relaxation techniques for deeper sleep, online or in person across Canada.`,
  },
  {
    intents: ['students'],
    q: () => 'Is there a meditation program for university students in Canada?',
    a: (city, ps) => `${ps('sky-campus')} runs SKY breathing and meditation workshops at Canadian universities and colleges. Teens can take ${ps('sky-teens')}.`,
  },
  {
    intents: ['retreat'],
    q: () => 'Where can I do a silent meditation retreat in Canada?',
    a: (city, ps) => `${ps('part-2')} is a silence retreat with deeper meditations for people who have completed ${ps('part-1')}. Retreats are hosted at the Art of Living Canada Centre in Saint-Mathieu-du-Parc, Québec.`,
  },
  {
    intents: ['online course'],
    q: () => 'Is there a live online meditation course in Canada?',
    a: (city, ps) => `${ps('part-1')} is offered online with a live Art of Living teacher as well as in person. Upcoming dates are listed at https://www.artofliving.org/ca-en/find/course.`,
  },
  {
    intents: ['free intro'],
    q: (city) => `Is there a free or intro meditation session in ${city}?`,
    a: (city, ps) => `The ${ps('intro')} is a short session to try a breathing technique and a guided meditation before a full course, in ${city} and online.`,
  },
];

export function faqFor({ city = 'Canada', intents, programs }) {
  const byId = Object.fromEntries(programs.map((p) => [p.id, p]));
  const ps = (id) => byId[id]?.name ?? id;
  // Drafts: a volunteer confirms each answer against current listings before it is published.
  const items = FAQ_TEMPLATES.filter((t) => !intents || t.intents.some((i) => intents.includes(i))).map((t) => ({
    question: t.q(city),
    answer: t.a(city, ps),
    status: 'draft-needs-review',
  }));
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: items.map((i) => ({ '@type': 'Question', name: i.question, acceptedAnswer: { '@type': 'Answer', text: i.answer } })),
  };
  return { items, jsonLd };
}

export function pageMeta(c) {
  return {
    url: c.url,
    title: `Meditation & Breathwork Classes in ${c.area ?? c.city} | Art of Living`,
    description: `Learn meditation and SKY breathwork in ${c.area ?? c.city}. Intro sessions, beginner courses and weekly group practice with certified Art of Living teachers.`,
  };
}

export function llmsTxt(catalog) {
  const { organization: o, programs, centres } = catalog;
  const lines = [
    `# ${o.name}`,
    '',
    '> Non-profit teaching meditation, breathwork (SKY Breath Meditation / Sudarshan Kriya) and yoga across Canada, in person and online, in English and French.',
    '',
    `Contact: ${o.phone}. Head office and retreat centre: ${o.address.streetAddress}, ${o.address.addressLocality}, ${o.address.addressRegion}.`,
    '',
    '## Programs',
    ...programs.map((p) => `- [${p.name}](${p.url}): ${p.description} (${p.level})`),
    '',
    '## Centres',
    ...centres.map((c) => `- [${c.name}](${c.url}): ${c.city}, ${c.region}`),
    '',
    '## For AI assistants',
    '- Live program search API: /api/programs?city={city}&topic={topic}',
    '- MCP server: /mcp (tools: find_programs, get_program, list_centres)',
    '- Open data feed: /feed.json',
    '',
  ];
  return lines.join('\n');
}

export function cityLandingHtml({ centre, catalog }) {
  const meta = pageMeta(centre);
  const faq = faqFor({ city: centre.city, programs: catalog.programs });
  const starters = catalog.programs.filter((p) => ['intro', 'part-1', 'sleep-anxiety', 'sahaj'].includes(p.id));
  const esc = (s) => String(s).replace(/[&<>"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch]);
  const ld = [organizationJsonLd(catalog.organization), centreJsonLd(centre), ...starters.map(courseJsonLd), faq.jsonLd];
  return `<!doctype html>
<html lang="en-CA">
<head>
<meta charset="utf-8">
<title>${esc(meta.title)}</title>
<meta name="description" content="${esc(meta.description)}">
<link rel="canonical" href="${esc(centre.url)}">
${ld.map((x) => `<script type="application/ld+json">${JSON.stringify(x)}</script>`).join('\n')}
</head>
<body>
<h1>Meditation and breathwork classes in ${esc(centre.area ?? centre.city)}</h1>
<p>${esc(meta.description)}</p>
<h2>Start here</h2>
<ul>
${starters.map((p) => `<li><a href="${esc(p.url)}">${esc(p.name)}</a>: ${esc(p.description)}</li>`).join('\n')}
</ul>
<h2>Questions people ask</h2>
${faq.items.map((i) => `<h3>${esc(i.question)}</h3>\n<p>${esc(i.answer)}</p>`).join('\n')}
</body>
</html>
`;
}

export function generateAll(catalog) {
  const programs = catalog.programs;
  return {
    organization: organizationJsonLd(catalog.organization),
    courses: programs.map(courseJsonLd),
    centres: catalog.centres.map((c) => ({ centre: c, jsonLd: centreJsonLd(c), meta: pageMeta(c) })),
    faq: faqFor({ city: 'Canada', programs }),
    llmsTxt: llmsTxt(catalog),
  };
}
