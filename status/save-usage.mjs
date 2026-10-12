// Saves a usage reading for the status page, and says whether the work may go on.
// Copied from an earlier project's status page (8 October 2026).
//   node "status/save-usage.mjs" <<'JSON'    (then the usage tool's output as JSON, then JSON)
//   node "status/save-usage.mjs" --by "Opus 5.5 · A2" <<'JSON' …
// Writes .status/usage.json (not in version history). The stop line is the
// "**Usage limit: N%**" in the roadmap, or the moving 5-hour line (H87); for the weekly limits it is earned over the week (stopLine in usage.mjs).
// Ends with code 0 when work may go on, 2 when it has to stop.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseRoadmap } from './parse.mjs';
import { ROADMAP } from './paths.mjs';
import { stopLine, usageReading, usageVerdict } from './usage.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const flag = process.argv.indexOf('--by');
const by = flag >= 0 ? (process.argv[flag + 1] ?? '') : 'HQ session';

// Phase L: a job the routine started in a Terminal window has no usage tool. Its status line
// (routine/statusline.py) saves what Claude Code knows of the plan limits; --statusline reads that.
//   node "status/save-usage.mjs" --statusline --by "Opus 5.5 · job 3"
// --gate: the routine's check before it starts a job, on the last saved reading (nothing is
// written; a window whose reset has passed counts as empty).
// F13: --weekly-only (with --gate or --statusline) for a job let past the line: it only goes past
// the 5-hour line; the weekly lines still count, so it waits at the weekly line like any other job.
// L10: --any takes the saved numbers whatever their age (the routine's usage check, every minute);
// the reading keeps the time they were really read, so the page shows how old they are.
const weeklyOnly = process.argv.includes('--weekly-only');
const LIVE = join(root, 'scratch/routine/usage-live.json');
const FRESH_MS = 10 * 60 * 1000;
let liveAt = null;
let liveBy = '';

function fromStatusline() {
  try {
    const raw = readFileSync(LIVE, 'utf8');
    const live = JSON.parse(raw);
    if (!process.argv.includes('--any') && Date.now() - Date.parse(live.savedAt) > FRESH_MS) return null;
    liveAt = new Date(live.savedAt);
    liveBy = live.by ?? '';
    const r = live.rate_limits ?? {};
    const win = (label, w) =>
      w && typeof w.used_percentage === 'number'
        ? { label, percentUsed: Math.round(w.used_percentage), resetsAt: w.resets_at ? new Date(w.resets_at * 1000).toISOString() : null }
        : null;
    const windows = [win('5-hour limit', r.five_hour), win('Weekly · all models', r.seven_day)].filter(Boolean);
    return windows.length ? { plan: { status: 'ok', plan: 'Max', windows } } : null;
  } catch {
    return null;
  }
}

if (process.argv.includes('--gate')) {
  const { usageLimit: limit, weeklyLimit: weekly, usageMoving: moving } = parseRoadmap(readFileSync(ROADMAP, 'utf8'));
  let saved = null;
  try {
    saved = JSON.parse(readFileSync(join(root, '.status/usage.json'), 'utf8'));
  } catch {}
  const now = new Date();
  if (saved?.readable) saved.limits = saved.limits.filter((l) => !l.resetsAt || Date.parse(l.resetsAt) > now.getTime());
  const v = usageVerdict(saved, limit, now, weekly, { weeklyOnly, moving });
  console.log(v.stop ? `STOP. ${v.reason}` : weeklyOnly ? 'OK to go on (past the 5-hour line; the weekly lines are under).' : 'OK to go on.');
  process.exit(v.stop ? 2 : 0);
}

let tool = null;
if (process.argv.includes('--statusline')) {
  tool = fromStatusline();
} else {
  try {
    tool = JSON.parse(readFileSync(0, 'utf8'));
  } catch {
    // Nothing readable came in: saved as a reading that could not be taken.
  }
}

const reading = usageReading(tool, {
  by: flag >= 0 || !liveBy ? by : liveBy,
  ...(liveAt && !Number.isNaN(liveAt.getTime()) ? { now: liveAt } : {}),
});
// F6/F7: the page always shows all three bars (5-hour, weekly all models, weekly Fable). A limit
// the last reading had and this one lacks is kept, marked as the last known reading, so the page
// shows it greyed out. A job's status line never knows Weekly Fable; a reading that fails knows
// nothing, so then every last number is kept, greyed out, instead of being wiped. A kept number
// never counts for the stop line (and a failed reading still stops the work). After its week has
// reset, the page shows a kept limit at zero, greyed out, until a fresh reading. A normal chat's
// full reading replaces them all.
if (process.argv.includes('--statusline') || !reading.readable) {
  let prev = null;
  try {
    prev = JSON.parse(readFileSync(join(root, '.status/usage.json'), 'utf8'));
  } catch {}
  const have = new Set(reading.limits.map((l) => l.label));
  for (const l of Array.isArray(prev?.limits) ? prev.limits : []) {
    if (have.has(l.label)) continue;
    reading.limits.push({ ...l, kept: true, keptAt: l.keptAt ?? prev.checkedAt, keptBy: l.keptBy ?? prev.by });
  }
}
mkdirSync(join(root, '.status'), { recursive: true });
writeFileSync(join(root, '.status/usage.json'), `${JSON.stringify(reading, null, 2)}\n`);

const { usageLimit: limit, weeklyLimit: weekly, usageMoving: moving } = parseRoadmap(readFileSync(ROADMAP, 'utf8'));
const verdict = usageVerdict(reading, limit, new Date(), weekly, { weeklyOnly, moving });
for (const l of reading.limits) {
  const at = stopLine(l, limit, new Date(), weekly, moving);
  if (l.kept) {
    const reset = l.resetsAt && Date.parse(l.resetsAt) <= Date.now();
    console.log(`${String(reset ? 0 : l.percent).padStart(3)}%  ${l.label}  (${reset ? `reset since ${l.resetsAt}` : `last known, read ${l.keptAt}`}; this session can't read it)`);
    continue;
  }
  console.log(`${String(l.percent).padStart(3)}%  ${l.label}${at ? `  (stop line ${at.line}%)` : ''}`);
}
if (reading.context) console.log(`${String(reading.context.percent).padStart(3)}%  Context window`);
console.log(
  verdict.stop
    ? `STOP. ${verdict.reason} Set the status block to STOPPED with this reason.`
    : `OK to go on${limit === null ? ' (the roadmap names no usage limit)' : weeklyOnly ? ': past the 5-hour line, and the weekly lines are under' : ': everything is under its stop line'}.`,
);
process.exit(verdict.stop ? 2 : 0);
