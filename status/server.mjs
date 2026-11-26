// HQ's status server, on this computer only (127.0.0.1, HQ_STATUS_PORT, 4748 by default). It answers what the app's page
// reads about HQ itself: the roadmap's status block (what's being worked on), the planning board and the hand-overs (read
// only), the work sessions as they were recorded, the routines and incidents, the laptop's readings, the usage, updates,
// the texts with the agents (the direct line), and the two HQs talking to each other (main and backup). The app's page
// reaches it through the call line (/status/... there), so it never needs a second address.
//   node "status/server.mjs"            start it and open it in the browser
//   node "status/server.mjs" --quiet    start it without opening a window
// Starting it a second time does nothing. It listens only on 127.0.0.1; the phone reaches HQ through Tailscale serve.
import { execFile, spawn } from 'node:child_process';
import { existsSync, openSync } from 'node:fs';
import { appendFile, mkdir, readdir, readFile, writeFile } from 'node:fs/promises';
import { createServer, request as httpRequest } from 'node:http';
import { request as httpsRequest } from 'node:https';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { gzipSync } from 'node:zlib';
import { parseRoadmap as parseRoadmapRaw } from './parse.mjs';
import { FOLDER, ROADMAP } from './paths.mjs';

// The planning file is over a megabyte: parsed once per change of the file, the same text gives the same result.
let parsedCache = { text: null, out: null };
function parseRoadmap(text) {
  if (parsedCache.text === text) return parsedCache.out;
  const out = parseRoadmapRaw(text);
  parsedCache = { text, out };
  return out;
}

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
// Beside the current HQ (HQ_BESIDE=1) this HQ's own routine doesn't run: health is read, never written, from the HQ whose routine does.
const healthRoot = (process.env.HQ_BESIDE === '1' && process.env.HQ_HEALTH_ROOT) || root;
const port = Number(process.env.HQ_STATUS_PORT ?? 4748);
const PY = existsSync(join(root, '.venv/bin/python')) ? join(root, '.venv/bin/python') : (process.env.HQ_PYTHON || '/usr/bin/python3');
const FILES = {
  '/apple-touch-icon.png': ['status/icons/hq-180.png', 'image/png'],
  '/apple-touch-icon-precomposed.png': ['status/icons/hq-180.png', 'image/png'],
  '/apple-touch-icon-180x180.png': ['status/icons/hq-180.png', 'image/png'],
  '/apple-touch-icon-180x180-precomposed.png': ['status/icons/hq-180.png', 'image/png'],
  '/favicon.ico': ['status/icons/hq-192.png', 'image/png'],
  '/icon-192.png': ['status/icons/hq-192.png', 'image/png'],
  '/icon-512.png': ['status/icons/hq-512.png', 'image/png'],
  // the installer's live checklist, also after the installer has ended
  '/install': ['install/checklist.html', 'text/html; charset=utf-8'],
  '/install.json': ['scratch/install/checklist.json', 'application/json; charset=utf-8'],
  '/hq-icon-180.png': ['status/icons/hq-180.png', 'image/png'],
  '/hq-icon-192.png': ['status/icons/hq-192.png', 'image/png'],
  '/hq-icon-512.png': ['status/icons/hq-512.png', 'image/png'],
  // the service worker for the agents' texts on the lock screen (scope /)
  '/direct-sw.js': ['status/direct-sw.js', 'text/javascript; charset=utf-8'],
};

// A second HQ (a server, HQ_LABEL set) gives its pages its own name and the night icon, so both sit on the phone's home
// screen side by side.
const LABEL = (process.env.HQ_LABEL ?? '').trim().replace(/[<>&"]/g, '');
const LABELLED = {
  '/apple-touch-icon.png': 'status/icons/hq-night-180.png',
  '/apple-touch-icon-precomposed.png': 'status/icons/hq-night-180.png',
  '/apple-touch-icon-180x180.png': 'status/icons/hq-night-180.png',
  '/apple-touch-icon-180x180-precomposed.png': 'status/icons/hq-night-180.png',
  '/favicon.ico': 'status/icons/hq-night-192.png',
  '/icon-192.png': 'status/icons/hq-night-192.png',
  '/icon-512.png': 'status/icons/hq-night-512.png',
  '/hq-icon-180.png': 'status/icons/hq-night-180.png',
  '/hq-icon-192.png': 'status/icons/hq-night-192.png',
  '/hq-icon-512.png': 'status/icons/hq-night-512.png',
};
// Which HQ this is: the label, else this computer (routine/hqpaths.py's where() says the same).
const OS_NAME = { darwin: 'macOS', linux: 'Linux', win32: 'Windows' }[process.platform] ?? process.platform;
const WHERE = LABEL || `Local · ${OS_NAME}`;
// A Mac is the laptop; on a server (Linux) there's no lid or battery. HQ_LAPTOP=1 or 0 overrides (tests).
const LAPTOP = process.env.HQ_LAPTOP ? process.env.HQ_LAPTOP === '1' : process.platform === 'darwin';

// The Mac app's judgement of how HQ is doing (desktop/hq_control.py), and its Turn everything on, which only starts what's
// off and never stops anything. The button needs the x-hq header, so a page from elsewhere can't press it.
function hqControl(args) {
  return new Promise((resolve) => {
    execFile('/usr/bin/python3', [join(root, 'desktop/hq_control.py'), ...args], { timeout: 60000 }, (err, out) => {
      try { resolve(JSON.parse(String(out).trim().split('\n').pop())); } catch { resolve(null); }
    });
  });
}


// F102: /routines.json never waits on a slow script. These scripts take 2 to 25 seconds on a real planning, and each read after the
// 20 seconds started its own run and waited for it, so every read in that stretch hung (a poller saw 8 and 25 seconds; flows 25
// and 54 gave up after 5). Now one run at a time goes on in the background and a read gets the last answer at once. Only with
// no answer yet does a read wait, FIRST_WAIT at most.
const FIRST_WAIT = 4000;
function kept(slot, ms, run) {
  if (Date.now() - slot.at >= ms && !slot.busy) {
    slot.busy = run().then((data) => {
      if (data !== null) slot.data = data;  // a run that failed keeps the last good answer
      slot.at = Date.now();
      slot.busy = null;
    });
  }
  if (slot.data !== null || !slot.busy) return Promise.resolve(slot.data);
  return Promise.race([slot.busy.then(() => slot.data), new Promise((r) => { setTimeout(() => r(slot.data), FIRST_WAIT); })]);
}


// The usage: this HQ's own reading, or the other HQ's when that's newer (only when two HQs are paired). The pairing is read
// from HQ_ROLE_READ when that names another HQ's memory (an HQ tried out beside another one), else from this HQ's own.
let peerUsage = { at: 0, data: null };
async function otherUsage() {
  if (Date.now() - peerUsage.at < Number(process.env.HQ_PEER_USAGE_CACHE ?? 20000)) return peerUsage.data;
  let c = null;
  try { c = JSON.parse(await readFile(join(process.env.HQ_ROLE_READ || SUPPORT, 'role.json'), 'utf8')); } catch {}
  if (!c?.peer) { peerUsage = { at: Date.now(), data: null }; return null; }
  const data = await new Promise((resolve) => {
    let url;
    try { url = new URL(`${c.peer.replace(/\/+$/, '')}/usage.json?own=1`); } catch { resolve(null); return; }
    const secure = url.protocol === 'https:';
    const opts = { method: 'GET', timeout: 3000, headers: { accept: 'application/json' } };
    if (secure && process.env.HQ_ROLE_INSECURE) opts.rejectUnauthorized = false;
    if (c.peer_ip) opts.lookup = (host, o, cb) => (o?.all ? cb(null, [{ address: c.peer_ip, family: c.peer_ip.includes(':') ? 6 : 4 }]) : cb(null, c.peer_ip, c.peer_ip.includes(':') ? 6 : 4));
    const req = (secure ? httpsRequest : httpRequest)(url, opts, (r) => {
      let b = '';
      r.on('data', (d) => { b += d; if (b.length > 200000) req.destroy(); });
      r.on('end', () => {
        try { resolve(r.statusCode === 200 ? JSON.parse(b) : null); } catch { resolve(null); }
      });
      r.on('error', () => resolve(null));
    });
    req.on('timeout', () => req.destroy());
    req.on('error', () => resolve(null));
    req.end();
  });
  const ok = data && typeof data === 'object' && !Number.isNaN(Date.parse(data.checkedAt));
  peerUsage = { at: Date.now(), data: ok ? { ...data, from: c.peer_name || 'the other HQ' } : null };
  return peerUsage.data;
}
async function usageStore() {
  return readStore('usage', join(root, '.status/usage.json'), { shape: isObject, missing: "There's no usage reading yet: work stops until a reading comes" });
}
async function usage(own, store = null) {
  const mine = (store ?? (await usageStore())).data;
  if (own) return mine;
  const other = await otherUsage();
  if (!other) return mine;
  if (!mine || Number.isNaN(Date.parse(mine?.checkedAt))) return other;
  // The newest reading wins; a tie goes to the other (the main's).
  return Date.parse(other.checkedAt) >= Date.parse(mine.checkedAt) ? other : mine;
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
      if (['status', 'start', 'check', 'clash'].includes(args[0])) upd = { at: Date.now(), data: args[0] === 'check' ? null : data };
      resolve(data);
    });
  });
}

// H56.1: HQ's own memory, the same folder as routine/hqpaths.py's support_dir(): HQ_SUPPORT, else on a Mac
// ~/Library/Application Support/HQ, else $XDG_STATE_HOME/hq (~/.local/state/hq).
const SUPPORT = process.env.HQ_SUPPORT
  || (process.platform === 'darwin' ? join(homedir(), 'Library/Application Support/HQ')
    : join(process.env.XDG_STATE_HOME || join(homedir(), '.local/state'), 'hq'));


// F106: one line on the page: the helpers beside a call, from their own records. A record past its box and a minute is left out.
async function forYouNow() {
  const dir = process.env.HQ_HELPERS || join(root, '.status/helpers');
  const out = [];
  let names = [];
  try { names = await readdir(dir); } catch { return out; }
  for (const n of names) {
    if (!n.endsWith('.json') || n.startsWith('live-')) continue;
    try {
      const d = JSON.parse(await readFile(join(dir, n), 'utf8'));
      const box = (d.box?.minutes ?? 5) * 60;
      if (d.state === 'running' && Date.now() / 1000 - d.started < box + 60) {
        out.push({ who: d.agent, question: String(d.question).slice(0, 120), since: d.started, box: d.box?.minutes ?? 5 });
      }
    } catch {}
  }
  return out;
}

// F116: a store the page reads, and whether it could. A file that isn't there is no reading yet (null), not broken, unless it
// must be there; a file that's there and can't be read is broken, with which one and why, so the page says so in red.

// A store the page reads, and whether it could. A file that isn't there is no reading yet (null), not broken, unless it
// must be there; a file that's there and can't be read is broken, with which one and why.
const STORE_WORDS = {
  routines: 'The routine lines', incidents: 'The incident log', usage: 'The saved usage reading', watchdog: "The watchdog's line",
  temperature: "The laptop's temperature", battery: "The laptop's battery", stats: "The laptop's totals", lidsleep: 'The lid-closed sleep',
};
function shortPath(path) {
  return path.startsWith(`${root}/`) ? path.slice(root.length + 1) : path.startsWith(`${FOLDER}/`) ? `workspace/${path.slice(FOLDER.length + 1)}` : path;
}
function brokenStore(store, path, why, say = null) {
  return { store, what: STORE_WORDS[store] ?? store, file: shortPath(path), why, ...(say ? { say } : {}) };
}
// F116, the check's 3: a file that isn't there is no reading, which the page says, never fine. `missing` is what to say then
// (red); `fresh` is what to say instead in a fresh install's first minutes (grey, not broken).
// The second check: "fresh" holds only while the installer's own process is alive (its pid in the checklist, and that pid really
// running install.py) and within FRESH_MIN of the install's start, whichever ends first. A start in the future, a test round
// (--test-only) or a checklist from before the pid was kept is never fresh: a killed install leaves "running" behind for good.
const FRESH_MIN = 30;
async function installerAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 1) return false;
  try { process.kill(pid, 0); } catch (e) { if (e.code !== 'EPERM') return false; }
  try {
    return (await readFile(`/proc/${pid}/cmdline`, 'utf8')).includes('install.py');
  } catch {
    return new Promise((resolve) => {
      execFile('ps', ['-p', String(pid), '-o', 'command='], { timeout: 3000 }, (err, out) => resolve(!err && String(out).includes('install.py')));
    });
  }
}
async function freshInstall() {
  try {
    const c = JSON.parse(await readFile(join(root, 'scratch/install/checklist.json'), 'utf8'));
    if (c?.mode === 'test' || c?.phase === 'test' || c?.finished) return false;
    const start = Date.parse(String(c?.run ?? '').replace(' ', 'T'));
    const age = Date.now() - start;
    if (!Number.isFinite(start) || age < -60000 || age > FRESH_MIN * 60000) return false;
    return await installerAlive(c.pid);
  } catch {
    return false;
  }
}
async function readStore(store, path, { must = false, shape = null, missing = null, fresh = false } = {}) {
  let text;
  try {
    text = await readFile(path, 'utf8');
  } catch (e) {
    if (e.code === 'ENOENT' && missing && !fresh) return { data: null, missing: true, broken: brokenStore(store, path, "it isn't there", missing) };
    if (e.code === 'ENOENT' && !must) return { data: null, missing: true, broken: null };
    return { data: null, broken: brokenStore(store, path, e.code === 'ENOENT' ? "it isn't there" : `it can't be opened (${e.code ?? e.message})`) };
  }
  let data;
  try {
    data = JSON.parse(text);
  } catch (e) {
    return { data: null, broken: brokenStore(store, path, `it can't be read: ${String(e.message).slice(0, 120)}`) };
  }
  if (shape && !shape(data)) return { data: null, broken: brokenStore(store, path, "it isn't in the shape it should be") };
  return { data, broken: null };
}
const isObject = (d) => d !== null && typeof d === 'object' && !Array.isArray(d);

// Every routine's own line, plus the watchdog's, which lives outside the Documents folder; the incidents; the laptop.
async function routines() {
  const broken = [];
  const missing = new Set();
  const fresh = await freshInstall();
  const read = async (store, path, opts) => {
    const r = await readStore(store, path, opts);
    if (r.broken) broken.push(r.broken);
    if (r.missing) missing.add(store);
    return r.data;
  };
  const ROUTINES_MISSING = "The routine hasn't written its lines: nothing here says whether anything runs";
  const data = (await read('routines', join(healthRoot, '.status/routines.json'), { shape: isObject, fresh, missing: ROUTINES_MISSING })) ?? {};
  if (!fresh && !broken.some((b) => b.store === 'routines') && Object.keys(data).length === 0 && !missing.has('routines')) {
    broken.push(brokenStore('routines', join(healthRoot, '.status/routines.json'), 'it holds no lines', ROUTINES_MISSING));
  }
  const dog = await read('watchdog', join(SUPPORT, 'watchdog.json'), { shape: isObject });
  if (dog) data.watchdog = dog;
  const inc = (await read('incidents', join(healthRoot, '.status/incidents.json'), { shape: (d) => isObject(d) && Array.isArray(d.incidents ?? []), fresh, missing: "There's no incident log: what went down isn't known from here" }))?.incidents ?? [];
  const temperature = await read('temperature', join(healthRoot, '.status/temperature.json'));
  const battery = await read('battery', join(healthRoot, '.status/battery.json'));
  const stats = await read('stats', join(healthRoot, '.status/stats.json'));
  const lidsleep = await read('lidsleep', join(healthRoot, '.status/lidsleep.json'));
  const forYou = await forYouNow();  // the helpers beside a call, looking something up for him right now
  const noLog = missing.has('incidents') && fresh;
  return { broken, noLog, forYou, laptop: LAPTOP, where: WHERE, now: Date.now() / 1000, routines: data, incidents: inc.slice(-30).reverse(), temperature, battery, stats, lidsleep };
}

// Being worked on: the roadmap's status block (status/set-status.py writes it), without the planning's tables.
async function statusBlock() {
  let text;
  try { text = await readFile(ROADMAP, 'utf8'); } catch (e) { return { error: e.code === 'ENOENT' ? "The planning isn't there" : `The planning can't be opened (${e.code ?? e.message})` }; }
  const p = parseRoadmap(text);
  const m = /Updated\s+(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}:\d{2}))?/.exec(p.updated ?? '');
  const t = m ? (m[2] ?? p.log?.[0]?.time) : null;
  const at = t ? new Date(`${m[1]}T${t.padStart(5, '0')}:00`).getTime() / 1000 : null;
  return { state: p.state, title: p.title, headline: p.headline, notes: p.notes, current: p.current, log: p.log, updated: p.updated,
    at: Number.isFinite(at) ? at : null, problems: p.problems, usageLines: p.usageLines };
}

// A Python reader's JSON answer (the planning board, the hand-overs), kept a short while so a page polling it costs nothing.
function pyJson(slot, ms, args) {
  return kept(slot, ms, () => new Promise((resolve) => {
    execFile(PY, args, { timeout: 30000, cwd: root, maxBuffer: 16 * 1024 * 1024 }, (err, out) => {
      try { resolve(err ? null : JSON.parse(String(out))); } catch { resolve(null); }
    });
  }));
}
const boardSlot = { at: 0, data: null, busy: null };
const handSlot = { at: 0, data: null, busy: null };

// Work sessions: the nights as HQ recorded them, one file each in the workspace's HQ/night-road/ (YYYY-MM-DD.json:
// {title, updated, running, rows: [{name, kind, start, end}], log: [{at, text}], usage: [{at, week}]}). Read only.
const SESSIONS = join(FOLDER, 'HQ', 'night-road');
async function sessions() {
  let names = [];
  try { names = (await readdir(SESSIONS)).map((f) => /^(\d{4}-\d{2}-\d{2})\.json$/.exec(f)?.[1]).filter(Boolean).sort().reverse(); } catch { return []; }
  const out = [];
  for (const key of names) {
    try {
      const n = JSON.parse(await readFile(join(SESSIONS, `${key}.json`), 'utf8'));
      out.push({ key, title: n.title ?? key, updated: n.updated ?? null, running: !!n.running, rows: Array.isArray(n.rows) ? n.rows.length : 0 });
    } catch { out.push({ key, title: key, broken: true }); }
  }
  return out;
}

function sendBody(req, res, code, type, body) {
  const head = { 'content-type': type, 'cache-control': 'no-store', vary: 'accept-encoding' };
  const buf = Buffer.isBuffer(body) ? body : Buffer.from(String(body));
  if (buf.length > 1024 && /\bgzip\b/.test(String(req.headers['accept-encoding'] ?? ''))) {
    res.writeHead(code, { ...head, 'content-encoding': 'gzip' }).end(gzipSync(buf));
  } else res.writeHead(code, head).end(buf);
}

// H23: every minute the state of each routine is written down, also when the helper is gone (its lines then
// go overdue, which counts as down), so the page can draw when each was up, running or down. A day is kept.

// Every minute the state of each routine is written down, also when the helper is gone (its lines then go overdue, which
// counts as down), so the page can draw when each was up, running or down. A day is kept.
const KEYS = ['helper', 'watchdog', 'mail', 'usage', 'phone', 'call', 'temp', 'battery'];
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
// 11 November 2026: builds can run side by side (routine/sidebyside.py): every running job gets its bar, not only the first.
let lastJobs = [];
async function sample() {
  try {
    const r = await routines();
    await appendFile(HISTORY, JSON.stringify({ t: Math.round(r.now), s: effective(r) }) + '\n');
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
// HQ_BESIDE=1: this HQ runs next to the current HQ on this computer, which keeps the texts' phones and sends the pushes.
const BESIDE = process.env.HQ_BESIDE === '1';
const DIRECT_PY = existsSync(join(root, '.venv/bin/python')) ? join(root, '.venv/bin/python') : '/usr/bin/python3';
const DIRECT_TOOL = join(root, 'app/direct_line.py');
// H266: Moneypenny's own line, /direct?line=team: her thread next to Donna's, the same phones and key.
const TEAM_DIR = process.env.HQ_TEAM_LINE_DIR ?? join(dirname(DIRECT_DIR), 'team-line');
let directInfo = null;
let teamInfo = null;
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
// What the page may see of the tool's info: the page's own reports stay out of it (F102, direct_line.py info shows them)
async function agentInfo(args) {
  const out = await directTool(args);
  if (out) delete out.page;
  return out;
}
async function threadLines(file) {
  try {
    return (await readFile(file, 'utf8')).split('\n').filter(Boolean).map((l) => {
      try { return JSON.parse(l); } catch { return null; }
    }).filter((m) => m && m.text);
  } catch {
    return [];
  }
}
// F58: on the backup its own lines wait in thread.here.jsonl (never synced) until the main's thread brings them back
async function directThread(dir = DIRECT_DIR) {
  const out = await threadLines(join(dir, 'thread.jsonl'));
  const mine = await threadLines(join(dir, 'thread.here.jsonl'));
  if (mine.length) {
    const key = (m) => m.id || `${Math.round(Number(m.at || 0) * 1000)}|${m.from}|${m.text}`; // F108: a line's own id, the old key for a line from before
    const have = new Set(out.map(key));
    const extra = mine.filter((m) => !have.has(key(m)));
    if (extra.length) return out.concat(extra).sort((a, b) => Number(a.at || 0) - Number(b.at || 0)).slice(-200);
  }
  return out.slice(-200);
}
async function directRoute(path0, req, res) {
  const json = (code, data) => res.writeHead(code, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(data));
  const team = new URL(req.url ?? '/', 'http://x').searchParams.get('line') === 'team';
  if (path0 === '/direct.json' && team) {
    if (!teamInfo || !teamInfo.key) teamInfo = (await agentInfo(['info', '--team'])) || teamInfo;
    // without Moneypenny the tool gives Donna: then her line is Donna's, as before
    const own = teamInfo && teamInfo.id !== (directInfo?.id ?? 'donna');
    return json(200, { agent: teamInfo, line: own ? 'team' : 'direct', messages: await directThread(own ? TEAM_DIR : DIRECT_DIR) });
  }
  if (path0 === '/direct/key' && BESIDE) return json(200, { key: '', beside: true });
  if (path0 === '/direct.json' || path0 === '/direct/key') {
    if (!directInfo || !directInfo.key) directInfo = (await agentInfo(['info'])) || directInfo;
    if (path0 === '/direct/key') return json(directInfo ? 200 : 500, { key: directInfo?.key ?? '' });
    return json(200, { agent: directInfo, line: 'direct', beside: BESIDE, messages: await directThread() });
  }
  if (req.method !== 'POST' || req.headers['x-hq'] !== 'direct') return res.writeHead(403).end('Only the HQ page can text her');
  let body = {};
  try { body = JSON.parse(await readBody(req)); } catch {}
  // Next to the current HQ (HQ_BESIDE=1) that one keeps the phones' list and sends every text and push: a sign-up or a
  // report from this page answers OK and changes nothing.
  if (BESIDE && (path0 === '/direct/subscribe' || path0 === '/direct/report')) return json(200, { ok: true, beside: true });
  if (path0 === '/direct/subscribe') {
    const out = await directTool(['subscribe'], JSON.stringify(body));
    if (out) directInfo = null;
    return json(out ? 200 : 400, out ?? { ok: false });
  }
  // F102: what the page or the worker saw; kept in HQ's .status by the tool, and nobody waits on it
  if (path0 === '/direct/report') {
    directTool(['report'], JSON.stringify(body)).catch(() => {});
    return json(200, { ok: true });
  }
  const text = String(body.text ?? '').trim().slice(0, 4000);
  if (!text) return json(400, { ok: false, said: 'nothing to send' });
  // H217: where the phone is, sent along only when he allows his location; kept by app/travel.py before she reads it
  if (body.lat != null && body.lon != null && /^-?[0-9.]+$/.test(String(body.lat)) && /^-?[0-9.]+$/.test(String(body.lon))) {
    await new Promise((done) => execFile(DIRECT_PY, [join(root, 'app/travel.py'), 'here', String(body.lat), String(body.lon)],
      { timeout: 10000, cwd: root }, () => done()));
  }
  if (body.line === 'team' && !teamInfo) teamInfo = await agentInfo(['info', '--team']);
  // H266: a text to Moneypenny goes into her own thread, and she answers it (the tool's --team)
  const toTeam = body.line === 'team' && teamInfo && teamInfo.id !== (directInfo?.id ?? 'donna');
  const dir = toTeam ? TEAM_DIR : DIRECT_DIR;
  await mkdir(dir, { recursive: true });
  // F58: through the tool's add(), so on the backup his text goes to the main (only the main writes the thread)
  const put = await directTool(['me', ...(toTeam ? ['--team'] : [])], JSON.stringify({ text }));
  if (!put) await appendFile(join(dir, 'thread.jsonl'), JSON.stringify({ at: Date.now() / 1000, from: 'me', text, why: '' }) + '\n');
  const log = openSync(join(root, 'scratch', 'direct-line.log'), 'a');
  spawn(DIRECT_PY, [DIRECT_TOOL, 'reply', ...(toTeam ? ['--team'] : [])], { cwd: root, detached: true, stdio: ['ignore', log, log] }).unref();
  return json(200, { ok: true });
}


// The pages this server used to show (the status page at /, the phone strip at /hq, the texts at /direct) are the app
// now, and so is anything else this server doesn't know: it's passed on to the call line on this computer, unchanged, so
// an old bookmark, the Mac app's tabs, the phone's old home-screen app and a tapped notification all get the app.
const CALL_PORT = Number(process.env.HQ_PORT ?? 7860);
function toCallLine(req, res) {
  const head = { ...req.headers };
  delete head.host;
  const up = httpRequest({ host: '127.0.0.1', port: CALL_PORT, method: req.method, path: req.url, headers: head }, (r) => {
    res.writeHead(r.statusCode ?? 502, r.headers);
    r.pipe(res);
  });
  up.on('error', () => { if (!res.headersSent) res.writeHead(502, { 'content-type': 'text/plain' }).end("HQ's call line can't be reached right now"); });
  req.pipe(up);
}

const server = createServer(async (req, res) => {
  const path0 = (req.url ?? '/').split('?')[0];
  if (path0 === '/direct.json' || path0 === '/direct/key' || path0 === '/direct/send' || path0 === '/direct/subscribe' || path0 === '/direct/report') {
    try { await directRoute(path0, req, res); } catch { if (!res.headersSent) res.writeHead(500).end('The direct line had a problem'); }
    return;
  }
  if (['/', '/index.html', '/hq', '/hq/', '/direct', '/direct/'].includes(path0)) {
    toCallLine(req, res);  // the app's page (see toCallLine)
    return;
  }
  if (path0 === '/api/update' || path0 === '/api/changelog') {
    const out = await updateTool([path0 === '/api/update' ? 'status' : 'changelog'], 4000);
    res.writeHead(out ? 200 : 500, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(JSON.stringify(out));
    return;
  }
  // After an update, a possible clash with their own extensions: talk it through, or it's fine.
  if (/^\/api\/update\/clash-(chat|ok)$/.test(path0)) {
    if (req.method !== 'POST' || req.headers['x-hq'] !== 'update') {
      res.writeHead(403).end('Only the HQ page can do this');
      return;
    }
    const out = await updateTool(['clash', path0.split('-').pop()]);
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
  // H191: the lid-closed sleep switch on the page (H45's line under Laptop), without a call: runs routine/lidsleep.py on
  // or off, which flips only through its one sudo -n command and says the setup line when that isn't done. Only on a
  // Mac (the laptop's own page; a server has no lid). Needs the x-hq header, so a page from elsewhere can't press it.
  if (path0 === '/api/lidsleep') {
    if (req.method !== 'POST' || req.headers['x-hq'] !== 'lidsleep') {
      res.writeHead(403).end('Only the HQ page can flip the lid-closed sleep');
      return;
    }
    let body = {};
    try { body = JSON.parse(await readBody(req)); } catch {}
    const json = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };
    if (!['on', 'off'].includes(body.want)) {
      res.writeHead(400).end('want is on or off');
      return;
    }
    if (!LAPTOP) {
      res.writeHead(409, json).end(JSON.stringify({ ok: false, said: 'Only on the laptop: this computer has no lid to switch.' }));
      return;
    }
    execFile(PY, [join(root, 'routine/lidsleep.py'), body.want], { timeout: 30000 }, (err, out, errOut) => {
      const said = String(out || errOut || '').trim() || (err ? 'It didn\'t answer.' : 'Done.');
      res.writeHead(err ? 400 : 200, json).end(JSON.stringify({ ok: !err, said }));
    });
    return;
  }
  // F115: the backup's every-minute hand-over to the main, on or off (routine/sync.py handover on|off, which the main
  // writes). Off on the real pair until the dry run has been read with him. Needs the x-hq header, as the lid's switch.
  if (path0 === '/api/handover') {
    if (req.method !== 'POST' || req.headers['x-hq'] !== 'handover') {
      res.writeHead(403).end('Only the HQ page can switch the hand-over');
      return;
    }
    let body = {};
    try { body = JSON.parse(await readBody(req)); } catch {}
    const json = { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' };
    if (!['on', 'off'].includes(body.want)) {
      res.writeHead(400).end('want is on or off');
      return;
    }
    execFile(PY, [join(root, 'routine/sync.py'), 'handover', body.want], { timeout: 120000 }, (err, out, errOut) => {
      const said = String(out || errOut || '').trim() || (err ? 'It didn\'t answer.' : 'Done.');
      res.writeHead(err ? 400 : 200, json).end(JSON.stringify({ ok: !err, said }));
    });
    return;
  }
  // H83: which HQ this is, for the call page (another port, so it may read only this, nothing else).
  // H118: and which computer is main (role.py's badge, with its routine line; none when this HQ is on its own).
  if (path0 === '/where.json') {
    let role = null;
    try { role = JSON.parse(await readFile(join(root, '.status/routines.json'), 'utf8'))?.role?.badge ?? null; } catch {}
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store', 'access-control-allow-origin': '*' })
      .end(JSON.stringify({ where: WHERE, role }));
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
  const json = (code, data) => sendBody(req, res, code, 'application/json; charset=utf-8', JSON.stringify(data));
  // Being worked on: the roadmap's status block.
  if (path0 === '/status.json') {
    const s = await statusBlock();
    json(s.error ? 500 : 200, s);
    return;
  }
  // The planning board, to look at: the open rows with their rank and MoSCoW tag (routine/planning_board.py).
  if (path0 === '/planning.json') {
    const b = await pyJson(boardSlot, 20000, [join(root, 'routine/planning_board.py')]);
    json(b ? 200 : 500, b ?? { error: "The planning couldn't be read" });
    return;
  }
  // The hand-overs: the notes prepared for building HQ by hand (routine/handovers.py), newest first; one by its name.
  if (path0 === '/handovers.json') {
    const h = await pyJson(handSlot, 10000, [join(root, 'routine/handovers.py')]);
    json(h ? 200 : 500, h ? { handovers: h } : { error: "The hand-overs couldn't be read" });
    return;
  }
  if (path0.startsWith('/handovers/')) {
    const name = decodeURIComponent(path0.slice('/handovers/'.length));
    const list = (await pyJson(handSlot, 10000, [join(root, 'routine/handovers.py')])) ?? [];
    const hit = list.find((x) => x.name === name);
    if (!hit) { json(404, { error: 'No such hand-over' }); return; }
    try {
      const text = await readFile(join(FOLDER, 'HQ', 'prep', hit.name), 'utf8');
      json(200, { ...hit, text });
    } catch { json(500, { error: "It can't be read" }); }
    return;
  }
  // Work sessions, as recorded: the list, and one by its day.
  if (path0 === '/sessions.json') {
    json(200, { sessions: await sessions() });
    return;
  }
  if (/^\/sessions\/\d{4}-\d{2}-\d{2}$/.test(path0)) {
    try {
      json(200, { key: path0.split('/')[2], ...JSON.parse(await readFile(join(SESSIONS, `${path0.split('/')[2]}.json`), 'utf8')) });
    } catch { json(404, { error: 'No such session' }); }
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/temperature-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    sendBody(req, res, 200, 'application/json; charset=utf-8', JSON.stringify({ now: Date.now() / 1000, samples: await temperatureHistory(hours) }));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/battery-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    sendBody(req, res, 200, 'application/json; charset=utf-8', JSON.stringify({ now: Date.now() / 1000, samples: await temperatureHistory(hours, '.status/battery-history.jsonl') }));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/stats-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    sendBody(req, res, 200, 'application/json; charset=utf-8', JSON.stringify({ now: Date.now() / 1000, samples: await temperatureHistory(hours, '.status/stats-history.jsonl') }));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/routines-history.json') {
    const hours = Number(new URL(req.url, 'http://x').searchParams.get('h') ?? 24) || 24;
    sendBody(req, res, 200, 'application/json; charset=utf-8', JSON.stringify({ now: Date.now() / 1000, samples: await history(hours) }));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/routines.json') {
    sendBody(req, res, 200, 'application/json; charset=utf-8', JSON.stringify(await routines()));
    return;
  }
  if ((req.url ?? '/').split('?')[0] === '/usage.json') {
    const own = new URL(req.url, 'http://x').searchParams.has('own');
    const u = await usage(own);
    res.writeHead(200, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' }).end(u ? `${JSON.stringify(u, null, 2)}\n` : 'null');
    return;
  }
  const entry = FILES[(req.url ?? '/').split('?')[0]];
  if (!entry) {
    toCallLine(req, res);  // the app's own files and API, for a page opened on this address
    return;
  }
  try {
    const path = (req.url ?? '/').split('?')[0];
    const file = (LABEL && LABELLED[path]) || entry[0];
    const body = await readFile(file.startsWith('/') ? file : join(root, file));
    res.writeHead(200, { 'content-type': entry[1], 'cache-control': 'no-store' }).end(body);
  } catch {
    // No checklist yet is not an error: the page says so.
    if (entry[0].endsWith('checklist.json')) {
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
  if (process.env.HQ_STATUS_TRIAL) return;  // a trial start only shows it answers; it writes no history
  sample();
  setInterval(sample, 60000);
  const url = `http://localhost:${port}`;
  console.log(`HQ status: ${url}`);
  // Opens in the default browser. Only on a fresh start, so no second tab appears.
  if (!process.argv.includes('--quiet')) execFile('open', [url]);
});
