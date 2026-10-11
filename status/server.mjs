// The HQ status page: http://localhost:4748 shows the status block of HQ/roadmap.md, always fresh.
// Copied from an earlier project's status page (8 October 2026). It serves the page, its two helpers, the roadmap as it is on disk,
// and the last usage reading a session saved with save-usage.mjs (.status/usage.json).
// A web page cannot ask Claude for the usage itself; only a session can, so a session writes it down.
//   node "status/server.mjs"            start it and open it in the browser
//   node "status/server.mjs" --quiet    start it without opening a window
// Starting it a second time does nothing: the page that is already open keeps working.
// It only listens on this MacBook (127.0.0.1), never on the network. The phone reaches it through
// Tailscale serve (tailnet only), set up by status/phone.sh (H13).
import { execFile } from 'node:child_process';
import { appendFile, readFile, writeFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseRoadmap } from './parse.mjs';
import { ROADMAP } from './paths.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const port = Number(process.env.HQ_STATUS_PORT ?? 4748);
const FILES = {
  '/': ['status/index.html', 'text/html; charset=utf-8'],
  '/index.html': ['status/index.html', 'text/html; charset=utf-8'],
  '/parse.mjs': ['status/parse.mjs', 'text/javascript; charset=utf-8'],
  '/usage.mjs': ['status/usage.mjs', 'text/javascript; charset=utf-8'],
  '/roadmap.md': [ROADMAP, 'text/markdown; charset=utf-8'],  // M1: in the workspace
  '/usage.json': ['.status/usage.json', 'application/json; charset=utf-8'],
  // H13: its own icon on the phone's home screen
  '/manifest.webmanifest': ['status/manifest.webmanifest', 'application/manifest+json'],
  '/apple-touch-icon.png': ['status/icons/apple-touch-icon.png', 'image/png'],
  '/icon-192.png': ['status/icons/icon-192.png', 'image/png'],
  '/icon-512.png': ['status/icons/icon-512.png', 'image/png'],
  // M4: the installer's live checklist, also after the installer has ended
  '/install': ['install/checklist.html', 'text/html; charset=utf-8'],
  '/install.json': ['scratch/install/checklist.json', 'application/json; charset=utf-8'],
  // H28: the phone version of the Mac app, at /hq (see hqPage below)
  '/hq/phone.js': ['desktop/phone.js', 'text/javascript; charset=utf-8'],
  '/hq/phone.css': ['desktop/phone.css', 'text/css; charset=utf-8'],
  '/hq.webmanifest': ['desktop/hq.webmanifest', 'application/manifest+json'],
  '/hq-icon-180.png': ['status/icons/hq-180.png', 'image/png'],
  '/hq-icon-192.png': ['status/icons/hq-192.png', 'image/png'],
  '/hq-icon-512.png': ['status/icons/hq-512.png', 'image/png'],
};

// H28: the phone version of the Mac app (H27). The Mac app's own strip (desktop/shell.html), unchanged, with
// the phone's script and look added, so the phone and the Mac always look the same. Its own home-screen icon.
const PHONE_HEAD = `
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="HQ">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="manifest" href="/hq.webmanifest">
<link rel="apple-touch-icon" href="/hq-icon-180.png">
<link rel="stylesheet" href="/hq/phone.css">
<script src="/hq/phone.js"></script>
`;
async function hqPage() {
  const shell = await readFile(join(root, 'desktop/shell.html'), 'utf8');
  return shell
    .replace(/<meta name="viewport"[^>]*>\n?/, '')
    .replace('</head>', PHONE_HEAD + '</head>')
    .replace('<body>', '<body class="phone">');
}
// H28: the same judgement the Mac app shows (desktop/hq_control.py), and its Turn everything on, which only
// starts what's off and never stops anything. The button needs the x-hq header, so a page from elsewhere
// can't press it (a plain form can't send that header).
function hqControl(args) {
  return new Promise((resolve) => {
    execFile('/usr/bin/python3', [join(root, 'desktop/hq_control.py'), ...args], { timeout: 60000 }, (err, out) => {
      try { resolve(JSON.parse(String(out).trim().split('\n').pop())); } catch { resolve(null); }
    });
  });
}

// H61: how long the jobs should take, from routine/estimate.py (learned from how long earlier jobs took).
// Asked at most every 20 seconds; the page polls every 3.
let est = { at: 0, data: null };
function estimates() {
  if (Date.now() - est.at < 20000) return Promise.resolve(est.data);
  return new Promise((resolve) => {
    execFile('/usr/bin/python3', [join(root, 'routine/estimate.py'), 'plan'], { timeout: 20000 }, (err, out) => {
      let data = null;
      try { data = JSON.parse(String(out).trim().split('\n').pop()); } catch {}
      est = { at: Date.now(), data };
      resolve(data);
    });
  });
}

// H19/H20: every routine's own line, plus the watchdog's, which lives outside the Documents folder.
async function routines() {
  const read = async (path) => {
    try { return JSON.parse(await readFile(path, 'utf8')); } catch { return null; }
  };
  const data = (await read(join(root, '.status/routines.json'))) ?? {};
  const dog = await read(join(homedir(), 'Library/Application Support/HQ/watchdog.json'));
  if (dog) data.watchdog = dog;
  // H30: the incident log (what went down, why, what was done, when it was back), newest first.
  const inc = (await read(join(root, '.status/incidents.json')))?.incidents ?? [];
  // H35: the laptop's latest temperature reading (routine/temperature.py, every minute).
  const temperature = await read(join(root, '.status/temperature.json'));
  // H37: the laptop's latest battery reading (routine/battery.py, every minute).
  const battery = await read(join(root, '.status/battery.json'));
  // H44: CPU, GPU, memory, disk and network (routine/stats.py, every minute).
  const stats = await read(join(root, '.status/stats.json'));
  // H45: whether the laptop keeps working with the lid closed (routine/lidsleep.py, every minute).
  const lidsleep = await read(join(root, '.status/lidsleep.json'));
  const estimate = await estimates();
  return { now: Date.now() / 1000, routines: data, incidents: inc.slice(-30).reverse(), temperature, battery, stats, lidsleep, estimate };
}

// H23: every minute the state of each routine is written down, also when the helper is gone (its lines then
// go overdue, which counts as down), so the page can draw when each was up, running or down. A day is kept.
const KEYS = ['helper', 'watchdog', 'mail', 'jobs', 'schedule', 'usage', 'phone', 'call', 'temp', 'battery'];
const HISTORY = join(root, '.status/routines-history.jsonl');
const DAY = 24 * 3600;
function effective(r) {
  const out = {};
  for (const k of KEYS) {
    const x = r.routines[k];
    if (!x) { out[k] = k === 'watchdog' ? 'down' : 'none'; continue; }
    const late = r.now - x.at > (x.every ?? 60) * 2 + 60;
    out[k] = late ? 'down' : x.state === 'fixed' ? 'ok' : (x.state ?? 'none');
  }
  return out;
}
// H33: which job runs and what the status block says it is doing, once a minute with the routines.
// 10 October 2026: "you see the different jobs, and you see their color and their status of their
// builds. So we can compare what went offline when we were building". "j" is a list of {n, st}, empty when
// no job runs; a sample with "j" marks the time the minute-by-minute record covers. A job that just finished
// gets one minute of DONE (or STOPPED, when it was stopped or ended without a done mark, or held by the usage line).
let lastJob = null;
async function jobsNow() {
  let p;
  try { p = parseRoadmap(await readFile(ROADMAP, 'utf8')); } catch { return null; }
  const jobs = p.queue.jobs;
  const out = [];
  if (lastJob !== null) {
    const was = jobs.find((x) => x.n === lastJob);
    if (was && !/^(running|stop asked)/.test(was.state)) {
      if (/^done/.test(was.state)) out.push({ n: was.n, st: 'DONE' });
      else if (/^(stopped|ended|held)/.test(was.state)) out.push({ n: was.n, st: 'STOPPED' });
      lastJob = null;
    }
  }
  const run = jobs.find((x) => /^(running|stop asked)/.test(x.state));
  if (run) {
    lastJob = run.n;
    out.push({ n: run.n, st: p.state ?? 'BUILDING' });
  } else if (p.state === 'STOPPED') {
    const held = jobs.find((x) => /^held/.test(x.state));
    if (held && !out.some((o) => o.n === held.n)) out.push({ n: held.n, st: 'STOPPED' });
  }
  return out;
}
const JOB_STATES = ['BUILDING', 'TESTING', 'RELEASING', 'WAITING', 'DONE', 'STOPPED'];
/** Per job, runs of the same state. Recorded minutes first; before the record starts, the backfill. */
async function jobsHistory(hours) {
  const now = Date.now() / 1000;
  const from = now - Math.min(24, Math.max(1, hours)) * 3600;
  let samples = [];
  try {
    samples = (await readFile(HISTORY, 'utf8')).split('\n').filter(Boolean).map((l) => {
      try { return JSON.parse(l); } catch { return null; }
    }).filter((x) => x && Array.isArray(x.j));
  } catch {}
  const since = samples[0]?.t ?? now;
  const segs = [];
  const open = {};
  for (const smp of samples) {
    for (const { n, st } of smp.j) {
      if (!JOB_STATES.includes(st)) continue;
      const run = open[n];
      if (run && run.st === st && smp.t - run.end <= 120) run.end = smp.t + 60;
      else { open[n] = { n, st, start: smp.t, end: smp.t + 60 }; segs.push(open[n]); }
    }
  }
  let texts = {};
  try {
    const file = JSON.parse(await readFile(join(root, '.status/jobs-backfill.json'), 'utf8'));
    const back = file.segments ?? [];
    texts = file.texts ?? {};
    for (const b of back) if (b.start < since && JOB_STATES.includes(b.st)) segs.push({ ...b, end: Math.min(b.end, since), filled: true });
  } catch {}
  return { now, since, texts, segments: segs.filter((x) => x.end > from && x.end > x.start).sort((a, b) => a.start - b.start) };
}
async function sample() {
  try {
    const r = await routines();
    const j = await jobsNow();
    await appendFile(HISTORY, JSON.stringify({ t: Math.round(r.now), s: effective(r), ...(j ? { j } : {}) }) + '\n');
    const lines = (await readFile(HISTORY, 'utf8')).split('\n').filter(Boolean);
    if (lines.length > 1500) await writeFile(HISTORY, lines.slice(-1440).join('\n') + '\n');
  } catch {}
}
async function history(hours) {
  const from = Date.now() / 1000 - Math.min(24, Math.max(1, hours)) * 3600;
  try {
    return (await readFile(HISTORY, 'utf8')).split('\n').filter(Boolean).map((l) => {
      try { return JSON.parse(l); } catch { return null; }
    }).filter((x) => x && x.t >= from);
  } catch {
    return [];
  }
}

// H35: the temperature over time, one reading a minute, written by routine/temperature.py (a day kept).
// H37: the battery the same way, from routine/battery.py.
async function temperatureHistory(hours, file = '.status/temperature-history.jsonl') {
  const from = Date.now() / 1000 - Math.min(24, Math.max(1, hours)) * 3600;
  try {
    return (await readFile(join(root, file), 'utf8')).split('\n').filter(Boolean).map((l) => {
      try { return JSON.parse(l); } catch { return null; }
    }).filter((x) => x && x.t >= from);
  } catch {
    return [];
  }
}

const server = createServer(async (req, res) => {
  const path0 = (req.url ?? '/').split('?')[0];
  if (path0 === '/hq' || path0 === '/hq/') {
    try {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' }).end(await hqPage());
    } catch {
      res.writeHead(500).end('Cannot read desktop/shell.html');
    }
    return;
  }
  if (path0 === '/hq.json') {
    const h = await hqControl(['health']);
    res.writeHead(h ? 200 : 500, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(h));
    return;
  }
  if (path0 === '/hq/fix') {
    if (req.method !== 'POST' || req.headers['x-hq'] !== 'fix') {
      res.writeHead(403).end('Only the HQ page can turn things on');
      return;
    }
    const out = await hqControl(['fix'].concat(process.env.HQ_FIX_DRY ? ['--dry'] : []));
    res.writeHead(out ? 200 : 500, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(out));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/temperature-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify({ now: Date.now() / 1000, samples: await temperatureHistory(hours) }));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/battery-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify({ now: Date.now() / 1000, samples: await temperatureHistory(hours, '.status/battery-history.jsonl') }));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/stats-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify({ now: Date.now() / 1000, samples: await temperatureHistory(hours, '.status/stats-history.jsonl') }));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/routines-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify({ now: Date.now() / 1000, samples: await history(hours) }));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/jobs-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(await jobsHistory(hours)));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/routines.json') {
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(await routines()));
    return;
  }
  const entry = FILES[(req.url ?? '/').split('?')[0]];
  if (!entry) {
    res.writeHead(404).end('Not found');
    return;
  }
  try {
    const body = await readFile(entry[0].startsWith('/') ? entry[0] : join(root, entry[0]));
    res.writeHead(200, { 'content-type': entry[1], 'cache-control': 'no-store' }).end(body);
  } catch {
    // No usage reading yet is not an error: the page says so.
    if (entry[0].endsWith('usage.json') || entry[0].endsWith('checklist.json')) {
      res.writeHead(200, { 'content-type': entry[1], 'cache-control': 'no-store' }).end('null');
      return;
    }
    res.writeHead(500).end(`Cannot read ${entry[0]}`);
  }
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.log(`HQ status is already running: http://localhost:${port}`);
    process.exit(0);
  }
  throw err;
});

server.listen(port, '127.0.0.1', () => {
  sample();
  setInterval(sample, 60000);
  const url = `http://localhost:${port}`;
  console.log(`HQ status: ${url}`);
  // Opens in the default browser. Only on a fresh start, so no second tab appears.
  if (!process.argv.includes('--quiet')) execFile('open', [url]);
});
