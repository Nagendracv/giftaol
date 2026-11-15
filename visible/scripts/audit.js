// Usage: node scripts/audit.js   (needs ANTHROPIC_API_KEY or an `ant auth login` profile)
import { runAudit } from '../src/audit/run.js';
import { loadQueries, saveRun } from '../src/data.js';
import { scoreRun } from '../src/score.js';

const { queries } = loadQueries();
const run = await runAudit({ queries, onProgress: (i, n, q) => console.log(`[${i}/${n}] ${q}`) });
const file = saveRun(run);
const s = scoreRun(run);
console.log(`Saved ${file}\nShare of voice (unbranded): ${s.shareOfVoice}%  branded recall: ${s.brandedRecall}%`);
