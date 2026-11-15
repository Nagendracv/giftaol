// Checks what a chatbot said about Art of Living against our own official catalog.
import { z } from 'zod';
import { zodOutputFormat } from '@anthropic-ai/sdk/helpers/zod';

export const AccuracySchema = z.object({
  claims: z.array(z.object({
    claim: z.string().describe('One statement the answer makes about Art of Living, quoted or closely paraphrased'),
    verdict: z.enum(['matches', 'wrong', 'not_in_our_facts']),
    explanation: z.string().describe('One plain sentence a volunteer can understand'),
  })),
});

export function factSheet(catalog) {
  const o = catalog.organization;
  return [
    `Organization: ${o.name}. Phone ${o.phone}. Retreat centre: ${o.address.streetAddress}, ${o.address.addressLocality}, ${o.address.addressRegion}.`,
    'Programs:',
    ...catalog.programs.map((p) => `- ${p.name} (${p.level}): ${p.description} ${p.url}`),
    'Centres:',
    ...catalog.centres.map((c) => `- ${c.name}, ${c.city} ${c.region}: ${c.url}`),
  ].join('\n');
}

export async function checkAccuracy(client, answer, catalog) {
  const response = await client.messages.parse({
    model: 'claude-opus-5-5',
    max_tokens: 8000,
    output_config: { effort: 'low', format: zodOutputFormat(AccuracySchema) },
    system:
      'You compare what a chatbot answer says about the Art of Living Foundation against the official fact sheet. ' +
      'List only statements about Art of Living, its programs, centres, prices, schedules or teachings. ' +
      'Mark "matches" only if the fact sheet supports it, "wrong" if the fact sheet contradicts it, otherwise "not_in_our_facts". ' +
      'Never use outside knowledge to judge a claim.',
    messages: [{ role: 'user', content: `<fact_sheet>\n${factSheet(catalog)}\n</fact_sheet>\n\n<chatbot_answer>\n${answer}\n</chatbot_answer>` }],
  });
  if (response.stop_reason === 'refusal' || !response.parsed_output) return { claims: [], error: 'Could not check this answer.' };
  return response.parsed_output;
}
