// The HQ status page: http://localhost:4748 shows the status block of HQ/roadmap.md, always fresh.
// Copied from an earlier project's status page (8 October 2026). It serves the page, its two helpers, the roadmap as it is on disk,
// and the last usage reading a session saved with save-usage.mjs (.status/usage.json).
// A web page cannot ask Claude for the usage itself; only a session can, so a session writes it down.
//   node "status/server.mjs"            start it and open it in the browser
//   node "status/server.mjs" --quiet    start it without opening a window
// Starting it a second time does nothing: the page that is already open keeps working.
// It only listens on this MacBook (127.0.0.1), never on the network. The phone reaches it through
// Tailscale serve (tailnet only), set up by status/phone.sh (H13).
import { execFile, spawn } from 'node:child_process';
import { existsSync, openSync } from 'node:fs';
import { appendFile, mkdir, readFile, writeFile } from 'node:fs/promises';
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
  // H80: the direct line, a chat with only her, and its service worker (scope /, for her texts on the lock screen)
  '/direct': ['status/direct.html', 'text/html; charset=utf-8'],
  '/direct-sw.js': ['status/direct-sw.js', 'text/javascript; charset=utf-8'],
  // H59: the version, a newer one and the changelog (the same file the call page loads)
  '/update-ui.js': ['status/update-ui.js', 'text/javascript; charset=utf-8'],
};

// H56.7: a second HQ (a server) gives its pages its own name and its own icons, so both sit on the phone's
// home screen side by side. HQ_LABEL (e.g. VPS); without it nothing changes. H84: its icon is HQ's house at
// night, with the stars and the moon (desktop/make_night_icon.py), for its status page and its /hq alike.
const LABEL = (process.env.HQ_LABEL ?? '').trim().replace(/[<>&"]/g, '');
const LABELLED = {
  '/apple-touch-icon.png': 'status/icons/hq-night-180.png',
  '/icon-192.png': 'status/icons/hq-night-192.png',
  '/icon-512.png': 'status/icons/hq-night-512.png',
  '/hq-icon-180.png': 'status/icons/hq-night-180.png',
  '/hq-icon-192.png': 'status/icons/hq-night-192.png',
  '/hq-icon-512.png': 'status/icons/hq-night-512.png',
};
// H83 (12 October 2026): which HQ this is, small under the name on the status page (and through
// hq_control.py's health on the phone version and in the Mac app): the label, else this computer.
// routine/hqpaths.py's where() says the same.
const OS_NAME = { darwin: 'macOS', linux: 'Linux', win32: 'Windows' }[process.platform] ?? process.platform;
const WHERE = LABEL || `Local · ${OS_NAME}`;
// H92: a Mac is the laptop; on a server (Linux) the page leaves the Laptop section out. HQ_LAPTOP=1 or 0 overrides (tests).
const LAPTOP = process.env.HQ_LAPTOP ? process.env.HQ_LAPTOP === '1' : process.platform === 'darwin';
function labelled(path, body) {
  if (path === '/' || path === '/index.html') {
    const page = String(body).replace('<meta name="hq-where" content="" />', `<meta name="hq-where" content="${WHERE}" />`)
      .replace('<meta name="hq-laptop" content="" />', `<meta name="hq-laptop" content="${LAPTOP ? 'yes' : 'no'}" />`);
    if (!LABEL) return page;
    return page
      .replace('<title>HQ · status</title>', `<title>HQ ${LABEL} · status</title>`)
      .replace('content="Status"', `content="Status ${LABEL}"`);
  }
  if (!LABEL) return body;
  if (path === '/manifest.webmanifest' || path === '/hq.webmanifest') {
    const m = JSON.parse(String(body));
    m.name = `${m.name} (${LABEL})`;
    m.short_name = `${m.short_name} ${LABEL}`;
    return JSON.stringify(m, null, 2);
  }
  return body;
}

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
  const head = LABEL ? PHONE_HEAD.replace('content="HQ"', `content="HQ ${LABEL}"`) : PHONE_HEAD;
  return shell
    .replace(/<meta name="viewport"[^>]*>\n?/, '')
    .replace('<title>HQ</title>', LABEL ? `<title>HQ ${LABEL}</title>` : '<title>HQ</title>')
    .replace('</head>', head + '</head>')
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

// H56.3: main and backup. The other HQ asks this one's role (GET /api/role), tells it a newer choice of main (POST
// /api/role) and, when this one is the main, hands it a call's change to the queue or the schedule (POST
// /api/forward). All of it is routine/role.py's; the posts need the x-hq header, so a page from elsewhere can't.
function roleTool(args, body) {
  return new Promise((resolve) => {
    const child = execFile('/usr/bin/python3', [join(root, 'routine/role.py'), 'serve', ...args], { timeout: 150000 }, (err, out) => {
      let data = null;
      try { data = JSON.parse(String(out).trim().split('\n').pop()); } catch {}
      resolve({ code: err?.code ?? 0, data });
    });
    child.stdin.end(body ?? '');
  });
}
function readBody(req) {
  return new Promise((resolve) => {
    let b = '';
    req.on('data', (c) => { b += c; if (b.length > 100000) req.destroy(); });
    req.on('end', () => resolve(b));
    req.on('error', () => resolve(''));
  });
}

// H59: the version, a newer one, the update and the changelog, from routine/update.py (the call server answers the
// same addresses). A look on GitHub is started in the background by update.py itself, a few times a day. Starting
// or checking needs the x-hq header, so a page from elsewhere can't press it.
let upd = { at: 0, data: null };
function updateTool(args, cacheMs = 0) {
  if (cacheMs && args[0] === 'status' && Date.now() - upd.at < cacheMs && upd.data) return Promise.resolve(upd.data);
  return new Promise((resolve) => {
    execFile('/usr/bin/python3', [join(root, 'routine/update.py'), ...args], { timeout: 120000 }, (err, out) => {
      let data = null;
      try { data = JSON.parse(String(out).trim().split('\n').pop()); } catch {}
      if (args[0] === 'status' || args[0] === 'start' || args[0] === 'check') upd = { at: Date.now(), data: args[0] === 'check' ? null : data };
      resolve(data);
    });
  });
}

// H56.1: HQ's own memory, the same folder as routine/hqpaths.py's support_dir(): HQ_SUPPORT, else on a Mac
// ~/Library/Application Support/HQ, else $XDG_STATE_HOME/hq (~/.local/state/hq).
const SUPPORT = process.env.HQ_SUPPORT
  || (process.platform === 'darwin' ? join(homedir(), 'Library/Application Support/HQ')
    : join(process.env.XDG_STATE_HOME || join(homedir(), '.local/state'), 'hq'));

// H19/H20: every routine's own line, plus the watchdog's, which lives outside the Documents folder.
async function routines() {
  const read = async (path) => {
    try { return JSON.parse(await readFile(path, 'utf8')); } catch { return null; }
  };
  const data = (await read(join(root, '.status/routines.json'))) ?? {};
  const dog = await read(join(SUPPORT, 'watchdog.json'));
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
  // H88: the heartbeat lines (beat-laptop, beat-vps, …) are named after the computers, so they're taken as they come.
  for (const k of [...KEYS, ...Object.keys(r.routines).filter((x) => x.startsWith('beat-'))]) {
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

// H80: the direct line. The thread is a file in the workspace (both computers have it through the sync); her
// name, colour and the push key come from app/direct_line.py, which also takes a phone's subscription and answers
// his texts (in the background, so the page doesn't wait). Every POST needs the x-hq header, so a page from
// elsewhere can't text her or sign a phone up; the server itself is only on this computer and the tailnet.
const DIRECT_DIR = process.env.HQ_DIRECT_DIR ?? join(dirname(ROADMAP), 'direct-line');
const DIRECT_PY = existsSync(join(root, '.venv/bin/python')) ? join(root, '.venv/bin/python') : '/usr/bin/python3';
const DIRECT_TOOL = join(root, 'app/direct_line.py');
let directInfo = null;
function directTool(args, input = '') {
  return new Promise((resolve) => {
    const p = execFile(DIRECT_PY, [DIRECT_TOOL, ...args], { timeout: 30000, cwd: root }, (err, out) => {
      let data = null;
      try { data = JSON.parse(String(out).trim().split('\n').pop()); } catch {}
      resolve(err ? null : data);
    });
    if (input) p.stdin.end(input); else p.stdin.end();
  });
}
async function directThread() {
  try {
    return (await readFile(join(DIRECT_DIR, 'thread.jsonl'), 'utf8')).split('\n').filter(Boolean).map((l) => {
      try { return JSON.parse(l); } catch { return null; }
    }).filter((m) => m && m.text).slice(-200);
  } catch {
    return [];
  }
}
async function directRoute(path0, req, res) {
  const json = (code, data) => res.writeHead(code, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(data));
  if (path0 === '/direct.json' || path0 === '/direct/key') {
    if (!directInfo || !directInfo.key) directInfo = (await directTool(['info'])) || directInfo;
    if (path0 === '/direct/key') return json(directInfo ? 200 : 500, { key: directInfo?.key ?? '' });
    return json(200, { agent: directInfo, messages: await directThread() });
  }
  if (req.method !== 'POST' || req.headers['x-hq'] !== 'direct') return res.writeHead(403).end('Only the HQ page can text her');
  let body = {};
  try { body = JSON.parse(await readBody(req)); } catch {}
  if (path0 === '/direct/subscribe') {
    const out = await directTool(['subscribe'], JSON.stringify(body));
    if (out) directInfo = null;
    return json(out ? 200 : 400, out ?? { ok: false });
  }
  const text = String(body.text ?? '').trim().slice(0, 4000);
  if (!text) return json(400, { ok: false, said: 'nothing to send' });
  await mkdir(DIRECT_DIR, { recursive: true });
  await appendFile(join(DIRECT_DIR, 'thread.jsonl'), JSON.stringify({ at: Date.now() / 1000, from: 'me', text, why: '' }) + '\n');
  const log = openSync(join(root, 'scratch', 'direct-line.log'), 'a');
  spawn(DIRECT_PY, [DIRECT_TOOL, 'reply'], { cwd: root, detached: true, stdio: ['ignore', log, log] }).unref();
  return json(200, { ok: true });
}

const server = createServer(async (req, res) => {
  const path0 = (req.url ?? '/').split('?')[0];
  if (path0 === '/direct.json' || path0 === '/direct/key' || path0 === '/direct/send' || path0 === '/direct/subscribe') {
    try { await directRoute(path0, req, res); } catch { if (!res.headersSent) res.writeHead(500).end('The direct line had a problem'); }
    return;
  }
  if (path0 === '/hq' || path0 === '/hq/') {
    try {
      res.writeHead(200, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' }).end(await hqPage());
    } catch {
      res.writeHead(500).end('Cannot read desktop/shell.html');
    }
    return;
  }
  if (path0 === '/api/update' || path0 === '/api/changelog') {
    const out = await updateTool([path0 === '/api/update' ? 'status' : 'changelog'], 4000);
    res.writeHead(out ? 200 : 500, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(out));
    return;
  }
  if (path0 === '/api/update/start' || path0 === '/api/update/check') {
    if (req.method !== 'POST' || req.headers['x-hq'] !== 'update') {
      res.writeHead(403).end('Only the HQ page can start an update');
      return;
    }
    let out = await updateTool(path0.endsWith('start') ? ['start'] : ['check', '--force']);
    if (path0.endsWith('check')) out = await updateTool(['status']);
    res.writeHead(out ? 200 : 500, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(out));
    return;
  }
  // H81: this computer's finished jobs (kind, minutes, its machine, tags; no job text), for the other HQ's estimates.
  if (path0 === '/api/estimates') {
    execFile('/usr/bin/python3', [join(root, 'routine/estimate.py'), 'share'], { timeout: 20000 }, (err, out) => {
      let data = null;
      try { data = JSON.parse(String(out).trim().split('\n').pop()); } catch {}
      res.writeHead(data ? 200 : 500, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(data));
    });
    return;
  }
  if (path0 === '/api/role' || path0 === '/api/forward') {
    const post = req.method === 'POST';
    if (post && req.headers['x-hq'] !== (path0 === '/api/role' ? 'role' : 'forward')) {
      res.writeHead(403).end('Only another HQ can ask this');
      return;
    }
    if (!post && path0 === '/api/forward') {
      res.writeHead(405).end('POST only');
      return;
    }
    const out = await roleTool([path0 === '/api/forward' ? 'forward' : post ? 'set' : 'get'], post ? await readBody(req) : '');
    const status = out.code === 3 ? 409 : out.code === 2 ? 400 : out.data ? 200 : 500;
    res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(out.data));
    return;
  }
  // H87, H91: the stop lines' switches on the page (each moving, or fixed at a number), through routine/usageline.py, which
  // writes it in the roadmap. Needs the x-hq header, so a page from elsewhere can't press it.
  if (path0 === '/api/usage-line') {
    if (req.method !== 'POST' || req.headers['x-hq'] !== 'usage-line') {
      res.writeHead(403).end('Only the HQ page can switch the usage lines');
      return;
    }
    let body = {};
    try { body = JSON.parse(await readBody(req)); } catch {}
    // H91: which line (five, weekly or fable; five when not named), then moving, or fixed with a number.
    const which = body.line == null ? 'five' : ['five', 'weekly', 'fable'].includes(body.line) ? body.line : null;
    const args = body.mode === 'moving' ? ['moving'] : body.mode === 'fixed' ? ['fixed'].concat(body.limit != null ? [String(body.limit)] : []) : null;
    if (!args || !which) {
      res.writeHead(400).end('line is five, weekly or fable; mode is moving or fixed');
      return;
    }
    execFile('/usr/bin/python3', [join(root, 'routine/usageline.py'), which, ...args], { timeout: 20000 }, (err, out, errOut) => {
      const said = String(err ? errOut || out : out).trim();
      res.writeHead(err ? 400 : 200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify({ ok: !err, said }));
    });
    return;
  }
  // H83: which HQ this is, for the call page (another port, so it may read only this, nothing else).
  if (path0 === '/where.json') {
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'access-control-allow-origin': '*' })
      .end(JSON.stringify({ where: WHERE }));
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
    const path = (req.url ?? '/').split('?')[0];
    const file = (LABEL && LABELLED[path]) || entry[0];
    const body = labelled(path, await readFile(file.startsWith('/') ? file : join(root, file)));
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
