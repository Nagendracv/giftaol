// Runs the audit: asks an AI engine each question and records whether Art of Living shows up.
import Anthropic from '@anthropic-ai/sdk';
import { isOwn } from '../score.js';

const MENTION = /art of living|sudarshan kriya|\bSKY (breath|campus|kids|teens)|sri sri yoga|sahaj samadhi/i;

const domainOf = (url) => {
  try { return new URL(url).hostname.toLowerCase(); } catch { return null; }
};

// Pull search-result domains and the answer text out of a Messages API response.
export function parseClaudeResponse(message) {
  const domains = [];
  const urls = [];
  let text = '';
  const cited = [];
  for (const block of message.content ?? []) {
    if (block.type === 'web_search_tool_result' && Array.isArray(block.content)) {
      for (const r of block.content) {
        if (r.type === 'web_search_result') {
          const d = domainOf(r.url);
          if (d) { domains.push(d); urls.push(r.url); }
        }
      }
    }
    if (block.type === 'text') {
      text += block.text;
      for (const c of block.citations ?? []) {
        const d = domainOf(c.url);
        if (d) cited.push(d);
      }
    }
  }
  const ownIdx = domains.findIndex(isOwn);
  const mentionedInAnswer = MENTION.test(text);
  const citedOwn = cited.some(isOwn);
  return {
    resultDomains: domains.slice(0, 10),
    resultUrls: urls.slice(0, 10),
    citedDomains: [...new Set(cited)],
    ownRank: ownIdx >= 0 && ownIdx < 10 ? ownIdx + 1 : null,
    mentionedInAnswer,
    citedOwn,
    mentioned: mentionedInAnswer || citedOwn,
    answerExcerpt: text.slice(0, 600),
    answer: text,
  };
}

export async function askClaude(client, q) {
  const message = await client.beta.messages.create({
    model: 'claude-opus-5-5',
    max_tokens: 4000,
    betas: ['server-side-fallback-2026-07-01'],
    fallbacks: 'default',
    output_config: { effort: 'low' },
    system:
      'You are a helpful assistant answering a member of the public in Canada. Search the web, then recommend specific places, courses or programs by name. Keep it to a short list.',
    tools: [{
      type: 'web_search_20260209', name: 'web_search', max_uses: 3,
      user_location: { type: 'approximate', country: 'CA', ...(q.city && q.city !== 'Canada' ? { city: q.city } : {}) },
    }],
    messages: [{ role: 'user', content: q.query }],
  });
  if (message.stop_reason === 'refusal') return { error: 'refusal' };
  return parseClaudeResponse(message);
}

export async function runAudit({ queries, client = new Anthropic(), label = 'REAL', onProgress } = {}) {
  const startedAt = new Date().toISOString();
  const results = [];
  for (const [i, q] of queries.entries()) {
    let r;
    try {
      r = await askClaude(client, q);
    } catch (err) {
      r = { error: err.message ?? String(err) };
    }
    const { answer, ...rest } = r; // keep stored runs small: excerpt only
    results.push({ ...q, engine: 'claude-opus-5-5+web_search', ...rest, mentioned: !!r.mentioned });
    onProgress?.(i + 1, queries.length, q.query);
  }
  return {
    runId: `audit-${startedAt.replace(/[:.]/g, '-')}`,
    runAt: startedAt,
    label,
    method: 'Each query was asked to Claude with live web search, located in Canada. A query counts when the answer names an Art of Living program or cites an Art of Living page.',
    queries: results,
  };
}
