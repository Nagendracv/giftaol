// Ready-to-post packages for one event, per platform, in the order that matters for AI answers.
// Eventbrite and Meetup are what chatbots cite most in our audit; Instagram is rarely cited, so it is last.

export const PLATFORMS = [
  { id: 'eventbrite', name: 'Eventbrite', how: 'api', citedIn: 'Most-used source in our audit (24 of 49 everyday questions).', titleMax: 75, summaryMax: 140 },
  { id: 'meetup', name: 'Meetup', how: 'copy', citedIn: 'Second most-used source (17 of 49).', titleMax: 80, open: 'https://www.meetup.com/home/', note: 'Posting through Meetup\'s API needs a paid Meetup Pro account, so Visible prepares the text and a volunteer pastes it into the group.' },
  { id: 'gbp', name: 'Google Business Profile', how: 'copy', citedIn: 'Feeds Google Maps and Google\'s AI answers for "near me" questions.', titleMax: 58, bodyMax: 1500, open: 'https://business.google.com/', note: 'Add it as an "Event" post on the centre\'s Google profile.' },
  { id: 'instagram', name: 'Instagram', how: 'copy', citedIn: 'Rarely cited by chatbots. Good for people who already follow us.', bodyMax: 2200, open: 'https://www.instagram.com/', note: 'Post from the centre\'s account with the event photo.' },
];

const PROVINCE_TZ = {
  BC: 'America/Vancouver', AB: 'America/Edmonton', SK: 'America/Regina', MB: 'America/Winnipeg',
  ON: 'America/Toronto', QC: 'America/Toronto', NB: 'America/Halifax', NS: 'America/Halifax', PE: 'America/Halifax', NL: 'America/St_Johns',
};
export const tzForProvince = (p) => PROVINCE_TZ[p] ?? 'America/Toronto';

const clip = (s, n) => (!n || s.length <= n ? s : s.slice(0, n - 1).trimEnd() + '…');

// "2026-12-03T19:00" in a time zone -> "2026-12-04T00:00:00Z".
export function zonedToUtc(local, timeZone) {
  const [d, t = '00:00'] = local.split('T');
  const [y, mo, da] = d.split('-').map(Number);
  const [h, mi] = t.split(':').map(Number);
  const guess = Date.UTC(y, mo - 1, da, h, mi);
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone, hourCycle: 'h23', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
  }).formatToParts(new Date(guess)).map((p) => [p.type, p.value]));
  const asZone = Date.UTC(+parts.year, +parts.month - 1, +parts.day, +parts.hour, +parts.minute);
  return new Date(guess - (asZone - guess)).toISOString().replace(/\.\d{3}Z$/, 'Z');
}

const whenText = (local, fr) => {
  if (!local) return fr ? '[date et heure]' : '[date and time]';
  const d = new Date(local + ':00');
  return d.toLocaleString(fr ? 'fr-CA' : 'en-CA', { weekday: 'long', month: 'long', day: 'numeric', hour: 'numeric', minute: '2-digit' });
};

// event: { programId, city, province, centreId?, start, end, venue?, online?, registrationUrl?, lang? }
export function eventPackages(catalog, event) {
  const program = catalog.programs.find((p) => p.id === event.programId) ?? catalog.programs[0];
  const centre = catalog.centres.find((c) => c.id === event.centreId) ?? catalog.centres.find((c) => c.city === event.city);
  const fr = event.lang === 'fr';
  const city = event.online ? (fr ? 'en ligne' : 'Online') : event.city;
  const hook = program.topics.includes('anxiety') ? (fr ? 'Respiration contre le stress et l\'anxiété' : 'Breathwork for Stress & Anxiety')
    : program.topics.includes('breathwork') ? (fr ? 'Respiration et méditation' : 'Breathwork & Meditation') : (fr ? 'Méditation' : 'Meditation');
  const where = event.online ? (fr ? ' en ligne' : ' (Online)') : (fr ? ` à ${city}` : ` in ${city}`);
  const reg = event.registrationUrl || program.url;
  const place = event.online ? (fr ? 'En ligne' : 'Online') : (event.venue || centre?.name || city);
  const lines = fr
    ? [program.description, '', `Quand : ${whenText(event.start, true)}`, `Où : ${place}`, '',
      `Animé par des enseignants certifiés de ${catalog.organization.name}, un organisme sans but lucratif.`, '', `Inscription : ${reg}`]
    : [program.description, '', `When: ${whenText(event.start)}`, `Where: ${place}`, '',
      `Led by certified teachers from ${catalog.organization.name}, a non-profit that has taught breathing and meditation across Canada for decades.`, '', `Register: ${reg}`];
  const body = lines.join('\n');
  const tags = [...new Set(['meditation', 'breathwork', 'stress relief', ...program.topics, `${String(city).toLowerCase()} meditation`, 'art of living'])];
  const base = `${hook}${where}: ${program.name}`;
  return PLATFORMS.map((p) => {
    if (p.id === 'instagram') {
      const hashtags = tags.slice(0, 8).map((t) => '#' + t.replace(/[^a-z0-9àâçéèêëîïôûùüÿ]/gi, ''));
      return { ...p, title: '', body: clip(`${hook}${where} ✨\n\n${program.name}\n${whenText(event.start, fr)} · ${place}\n\n${fr ? 'Lien d\'inscription dans la bio' : 'Registration link in bio'}\n\n${hashtags.join(' ')}`, p.bodyMax) };
    }
    return {
      ...p, title: clip(base, p.titleMax), body: clip(body, p.bodyMax),
      summary: p.summaryMax ? clip(`${hook}${where}. ${program.description}`, p.summaryMax) : undefined,
      tags: tags.slice(0, 10),
    };
  });
}
