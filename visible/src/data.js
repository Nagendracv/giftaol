import { readFileSync, readdirSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

export const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
export const DATA = join(ROOT, 'data');
export const AUDITS = join(DATA, 'audits');

const readJson = (p) => JSON.parse(readFileSync(p, 'utf8'));

export const loadCatalog = () => readJson(join(DATA, 'programs.json'));
export const loadSiteFacts = () => readJson(join(DATA, 'site-facts.json'));
export const loadQueries = () => readJson(join(DATA, 'queries.json'));

export function listRuns() {
  if (!existsSync(AUDITS)) return [];
  return readdirSync(AUDITS)
    .filter((f) => f.endsWith('.json'))
    .map((f) => readJson(join(AUDITS, f)))
    .sort((a, b) => a.runAt.localeCompare(b.runAt));
}

export function saveRun(run) {
  mkdirSync(AUDITS, { recursive: true });
  const file = join(AUDITS, `${run.runId}.json`);
  writeFileSync(file, JSON.stringify(run, null, 1));
  return file;
}
