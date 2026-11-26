// Saves a usage reading for the status page, and prints the numbers with the stop line each has on the roadmap.
//   node "status/save-usage.mjs" <<'JSON'    (then the usage tool's output as JSON, then JSON)
//   node "status/save-usage.mjs" --by "Opus 5.5 · a chat" <<'JSON' …
//   node "status/save-usage.mjs" --statusline [--any] --by "…"   what Claude Code's status line saved (routine/statusline.py)
// Writes .status/usage.json (not in version history). --any takes the saved numbers whatever their age (the routine's
// usage check, every minute); the reading keeps the time they were really read, so the page shows how old they are.
// HQ_USAGE reads and writes a test's own reading.
import { mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseRoadmap } from './parse.mjs';
import { ROADMAP } from './paths.mjs';
import { lineKey, stopLine, usageReading } from './usage.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const flag = process.argv.indexOf('--by');
const by = flag >= 0 ? (process.argv[flag + 1] ?? '') : 'HQ session';

// F198: a test writes usage only into its own copy, never HQ's real file. A reading whose by names a test (like "F-something test")
// without HQ_USAGE goes to its own workspace's .status/usage.json when the test runs on a workspace of its own
// (HQ_WORKSPACE elsewhere than HQ's); otherwise it's refused before anything is written (exit 3), and the refusal is logged in HQ's
// .status/usage-refused.json: the newest refusal (its time, the refused reading's by, why), rewritten at each one.
const REAL_USAGE = join(root, '.status/usage.json');
const byNamesTest = (b) => /\btests?\b/i.test(b ?? '');
const realPath = (p) => { try { return realpathSync(p); } catch { return resolve(p); } };
const ownWorkspace = process.env.HQ_WORKSPACE && realPath(process.env.HQ_WORKSPACE) !== realPath(join(root, 'workspace'))
  ? process.env.HQ_WORKSPACE : null;
const USAGE_FILE = process.env.HQ_USAGE || (byNamesTest(by) && ownWorkspace ? join(ownWorkspace, '.status/usage.json') : REAL_USAGE);
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
    let name = 'Max';  // a status line doesn't say the plan: the last reading's name stays
    try { name = JSON.parse(readFileSync(USAGE_FILE, 'utf8')).plan || name; } catch {}
    return windows.length ? { plan: { status: 'ok', plan: name, windows } } : null;
  } catch {
    return null;
  }
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
    prev = JSON.parse(readFileSync(USAGE_FILE, 'utf8'));
  } catch {}
  const have = new Set(reading.limits.map((l) => l.label));
  for (const l of Array.isArray(prev?.limits) ? prev.limits : []) {
    if (have.has(l.label)) continue;
    // F107: a reading that works and has no 5-hour window is a plan without that limit, not a number it couldn't read. On Max 5x
    // that happened once in 3,938 readings; a next reading with one puts it right back.
    if (reading.readable && lineKey(l.label) === 'five') continue;
    reading.limits.push({ ...l, kept: true, keptAt: l.keptAt ?? prev.checkedAt, keptBy: l.keptBy ?? prev.by });
  }
}
if (byNamesTest(reading.by) && realPath(USAGE_FILE) === realPath(REAL_USAGE)) {
  const refused = { at: new Date().toISOString(), by: reading.by, why: "a test's reading never goes into HQ's real usage file (F198); HQ_USAGE points a test at its own copy" };
  try { mkdirSync(join(root, '.status'), { recursive: true }); writeFileSync(join(root, '.status/usage-refused.json'), `${JSON.stringify(refused, null, 1)}\n`); } catch {}
  console.log(`Refused: a reading by "${reading.by}" names a test, and a test's reading goes only into its own copy (HQ_USAGE), never HQ's real usage file. Logged in .status/usage-refused.json.`);
  process.exit(3);
}
mkdirSync(dirname(USAGE_FILE), { recursive: true });
writeFileSync(USAGE_FILE, `${JSON.stringify(reading, null, 2)}\n`);
const { usageLines: lines } = parseRoadmap(readFileSync(ROADMAP, 'utf8'));
for (const l of reading.limits) {
  const at = stopLine(l, lines, new Date());
  if (l.kept) {
    const reset = l.resetsAt && Date.parse(l.resetsAt) <= Date.now();
    console.log(`${String(reset ? 0 : l.percent).padStart(3)}%  ${l.label}  (${reset ? `reset since ${l.resetsAt}` : `last known, read ${l.keptAt}`}; this session can't read it)`);
    continue;
  }
  console.log(`${String(l.percent).padStart(3)}%  ${l.label}${at ? `  (stop line ${at.line}%)` : ''}`);
}
if (reading.context) console.log(`${String(reading.context.percent).padStart(3)}%  Context window`);
if (!reading.readable) console.log('The usage could not be read; the last known numbers are kept.');
