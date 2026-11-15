// French materials for Québec: FAQ and event listings. Drafts: a francophone teacher checks before publishing.
const DESC_FR = {
  'part-1': "Cours de respiration et de méditation centré sur SKY / Sudarshan Kriya, une technique de respiration rythmée, avec méditation guidée et outils pratiques contre le stress.",
  intro: "Courte séance d'introduction pour essayer une technique de respiration et une méditation guidée avant un cours complet.",
  'sleep-anxiety': "Programme court de respiration et de relaxation pour mieux dormir et apaiser l'anxiété.",
  sahaj: 'Méditation avec mantra, transmise personnellement à chaque participant, pour une pratique quotidienne sans effort.',
  'part-2': "Retraite en silence avec méditations plus profondes, pour les personnes ayant suivi la Partie 1.",
};

export function faqFr({ city = 'au Québec', programs }) {
  const byId = Object.fromEntries(programs.map((p) => [p.id, p.name]));
  const where = city === 'au Québec' ? 'au Québec' : `à ${city}`;
  const items = [
    { question: `Où apprendre la méditation ${where} ?`, answer: `La Fondation Art de Vivre enseigne la méditation ${where} et en ligne partout au Canada. Les débutants commencent souvent par ${byId['part-1']} ou par l'${byId.intro}.` },
    { question: `Y a-t-il des cours de respiration (breathwork) ${where} ?`, answer: `Oui. ${byId['part-1']} enseigne la méditation SKY (Sudarshan Kriya), une technique de respiration rythmée. Les participants peuvent ensuite pratiquer en groupe chaque semaine.` },
    { question: 'Existe-t-il un atelier de respiration contre le stress ou l’anxiété ?', answer: `${byId['sleep-anxiety']} propose des techniques de respiration et de relaxation pour l'anxiété et le sommeil. ${byId['part-1']} va plus loin avec la méditation SKY, étudiée dans des recherches publiées sur le stress et l'anxiété.` },
    { question: 'Où faire une retraite de méditation en silence au Québec ?', answer: `${byId['part-2']} est une retraite en silence offerte au Centre Art de Vivre Canada, à Saint-Mathieu-du-Parc en Mauricie, pour les personnes ayant suivi ${byId['part-1']}.` },
  ].map((i) => ({ ...i, status: 'brouillon-a-verifier' }));
  return {
    items,
    jsonLd: {
      '@context': 'https://schema.org', '@type': 'FAQPage', inLanguage: 'fr-CA',
      mainEntity: items.map((i) => ({ '@type': 'Question', name: i.question, acceptedAnswer: { '@type': 'Answer', text: i.answer } })),
    },
  };
}

export function listingsFr({ catalog, cities, platforms = ['Eventbrite', 'Meetup'] }) {
  const out = [];
  for (const platform of platforms) {
    for (const id of ['intro', 'part-1', 'sleep-anxiety']) {
      const p = catalog.programs.find((x) => x.id === id);
      for (const city of cities) {
        const hook = id === 'sleep-anxiety' ? 'Respiration contre le stress et l’anxiété' : 'Méditation et respiration';
        const title = `${hook} à ${city} : ${p.name}`.slice(0, 75);
        out.push({
          platform: `${platform} (français)`, title,
          tags: ['méditation', 'respiration', 'gestion du stress', 'pleine conscience', `méditation ${city.toLowerCase()}`, 'art de vivre', 'SKY'],
          body: `${DESC_FR[id]}\n\nAnimé par des enseignants certifiés de la Fondation Art de Vivre, un organisme sans but lucratif.\n\nPage officielle : ${p.url.replace('/ca-en/', '/ca-fr/')}\nToutes les dates : https://www.artofliving.org/ca-fr/find/course`,
          link: p.url, lang: 'fr',
        });
      }
    }
  }
  return out;
}
