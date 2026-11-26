// Moneypenny's area: hand-overs, status, the planning board, work sessions, health, updates.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
//
// The real data comes from the status server (/status/...) and the call line's update
// endpoints, read only, as API.md lists them. Everything the templates show is under one
// value, `mpv` (built the same way from the demo module in demo mode); the prototypes'
// own values are still given, unchanged, for the demo and its equivalence check.
import * as demo from './demo/mp.js';

export const NAME = 'mp';
export const WIRED = true;
export { demo };

export const start = { updating: 0, mpHandover: null, mpSession: null, mpUpdBusy: false, mpUpdSaid: '' };

// ---- the real data -------------------------------------------------------------------

// One piece of state.data.mp at a time, so one slow or failed read never holds the rest.
const PIECES = {
  status: 'status/status.json', usage: 'status/usage.json', routines: 'status/routines.json',
  handovers: 'status/handovers.json', planning: 'status/planning.json', sessions: 'status/sessions.json',
  update: 'api/update', changelog: 'api/changelog', calls: 'api/calls', team: 'direct.json?line=team'
};
function put(app, patch) {
  app.setData(NAME, (o) => {
    const x = Object.assign({ err: {} }, o || {});
    for (const k in patch) if (k !== 'err') x[k] = patch[k];
    x.err = Object.assign({}, x.err, patch.err || {});
    return x;
  });
}
async function read(app, key, path) {
  try {
    const v = await app.api.get(path || PIECES[key]);
    put(app, { [key]: v, err: { [key]: '' } });
    return v;
  } catch (e) {
    put(app, { err: { [key]: e.message || 'failed' } });
    return null;
  }
}
const readAll = (app, keys) => Promise.all(keys.map((k) => read(app, k)));

let timer = 0, updTimer = 0;
export async function load(app) {
  put(app, {});
  await readAll(app, Object.keys(PIECES));
  // The status page reads its numbers again every few seconds; here every 30 seconds is
  // enough, and only while the page is shown.
  if (!timer && typeof setInterval !== 'undefined') {
    timer = setInterval(() => {
      if (typeof document !== 'undefined' && document.hidden) return;
      readAll(app, ['status', 'usage', 'routines']);
    }, 30000);
  }
  pollUpdate(app);
}

// While an update runs, its state is read every 3 seconds (as the old page's update bar).
function pollUpdate(app) {
  clearTimeout(updTimer);
  const u = app.state.data.mp && app.state.data.mp.update;
  if (u && u.run && (u.run.state === 'waiting' || u.run.state === 'updating')) {
    updTimer = setTimeout(async () => { await read(app, 'update'); pollUpdate(app); }, 3000);
  }
}

async function openSession(app, key) {
  app.setState({ mpSession: key });
  const v = await read(app, 'session:' + key, 'status/sessions/' + encodeURIComponent(key));
  if (v) app.setData(NAME, (o) => Object.assign({}, o, { days: Object.assign({}, o && o.days, { [key]: v }) }));
}
async function openHandover(app, name) {
  app.setState({ mpHandover: name });
  app.go('handover');
  const v = await read(app, 'handover:' + name, 'status/handovers/' + encodeURIComponent(name));
  if (v) app.setData(NAME, (o) => Object.assign({}, o, { texts: Object.assign({}, o && o.texts, { [name]: v }) }));
}

export const enter = {
  status: (app) => readAll(app, ['status', 'usage', 'routines', 'update']),
  health: (app) => read(app, 'routines'),
  planning: (app) => read(app, 'planning'),
  handovers: (app) => read(app, 'handovers'),
  updates: (app) => readAll(app, ['update', 'changelog']),
  sessions: async (app) => {
    const s = await read(app, 'sessions');
    const list = (s && s.sessions) || [];
    const pick = app.state.mpSession || (list.find((x) => x.rows > 0) || list[0] || {}).key;
    if (pick) openSession(app, pick);
  }
};

// ---- words and times --------------------------------------------------------------------

const ago = (ms) => {
  const min = Math.round(ms / 60000);
  if (min < 1) return 'just now';
  if (min < 60) return min + ' min ago';
  const h = Math.floor(min / 60);
  return h < 24 ? h + ' h ' + (min % 60) + ' min ago' : Math.floor(h / 24) + ' days ago';
};
const until = (iso) => {
  const min = Math.round((new Date(iso).getTime() - Date.now()) / 60000);
  if (!(min > 0)) return 'resets now';
  const h = Math.floor(min / 60);
  if (h >= 24) return 'resets in ' + Math.floor(h / 24) + ' d ' + (h % 24) + ' h';
  return h > 0 ? 'resets in ' + h + ' h ' + (min % 60) + ' min' : 'resets in ' + min + ' min';
};
const hm = (d) => d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
const clock = (d) => (d.toDateString() === new Date().toDateString() ? '' : d.toLocaleDateString('en-GB', { weekday: 'short' }) + ' ') + hm(d);
const dayWords = (iso) => {
  const d = new Date(String(iso).slice(0, 10) + 'T12:00:00'); if (isNaN(d)) return iso || '';
  const t = new Date(); const y = new Date(t.getFullYear(), t.getMonth(), t.getDate() - 1);
  if (d.toDateString() === t.toDateString()) return 'today';
  if (d.toDateString() === y.toDateString()) return 'yesterday';
  return d.toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
};
const cap = (s) => String(s || '').replace(/^./, (c) => c.toUpperCase());

const STATE = {
  BUILDING: ['Building', '#ca8a04'], TESTING: ['Testing', '#ca8a04'], RELEASING: ['Releasing', '#ca8a04'],
  WAITING: ['Waiting for you', '#6d28d9'], DONE: ['Done', '#16a34a'], STOPPED: ['Stopped', '#b42318']
};

// The routine lines in the order and with the names the old status page uses.
const ROUTINES = [
  ['role', 'Main or backup'], ['sync', 'Two-way sync'], ['helper', 'Routine helper'], ['watchdog', 'Watchdog'],
  ['mail', 'Mail check'], ['jobs', 'Jobs from calls'], ['schedule', 'Scheduler'], ['usage', 'Usage check'],
  ['phone', 'Status page'], ['call', 'Call line'], ['extensions', 'Your own routines'], ['maillist', 'Mail list'],
  ['mailmarker', 'Newest mail seen'], ['mailreach', 'Mail read in full'], ['saving', 'Saving to GitHub'],
  ['review', 'Reviewer'], ['qa', 'QA'], ['nightly', 'The night’s tests'], ['release', 'Release'],
  ['cycles', 'The agents’ cycles'], ['briefing', 'Briefing'], ['routines-file', 'The routine lines'],
  ['incidents-file', 'The incident log'], ['mistakes', 'The ledger of mistakes'], ['feedback', 'Feedback mailbox'],
  ['data', 'Data changes'], ['record', 'The record of each item'], ['helpers', 'Helpers beside a call'],
  ['about', 'GitHub’s About'], ['donna', 'Donna’s watch'], ['reminders', 'Your reminders'], ['weather', 'Weather'],
  ['news', 'Your news'], ['calendar', 'Calendar read'], ['coaching', 'Coaching check-ins'],
  ['temp', 'Laptop temperature'], ['battery', 'Laptop battery']
];
// The lines always shown; the rest (and the heartbeats) only once they've written a line.
const ALWAYS = new Set(['helper', 'watchdog', 'mail', 'jobs', 'schedule', 'usage', 'phone', 'call', 'temp', 'battery']);
const DOT = { ok: '#16a34a', fixed: '#16a34a', running: '#2563eb', waiting: '#ca8a04', warm: '#d97706', low: '#d97706', down: '#dc2626', off: '#94a3b8' };

function health(r) {
  if (!r) return null;
  const now = r.now || Date.now() / 1000;
  const all = r.routines || {};
  const helper = all.helper;
  const helperLate = !helper || now - helper.at > 180;
  const rows = [];
  let bad = 0, busy = 0, waiting = 0;
  for (const b of r.broken || []) { bad++; rows.push({ n: b.what, l: b.say || ('Can’t read it: ' + b.why), dot: DOT.down, key: 'broken:' + b.store }); }
  const beats = Object.keys(all).filter((k) => k.startsWith('beat-')).sort().map((k) => [k, (all[k] && all[k].name) || k.slice(5)]);
  const i = ROUTINES.findIndex(([k]) => k === 'helper');
  const order = ROUTINES.slice(0, i).concat(beats, ROUTINES.slice(i)).filter(([k]) => r.laptop || (k !== 'temp' && k !== 'battery'));
  for (const [key, name] of order) {
    const x = all[key];
    if (!x && !ALWAYS.has(key)) continue;
    let state = (x && x.state) || 'off';
    let text = (x && x.text) || 'No line yet';
    const late = x && now - x.at > (x.every || 60) * 2 + 60;
    if (!x && key === 'watchdog') { state = 'down'; text = 'Not installed or not running'; }
    else if (late) {
      state = 'down';
      text = key === 'helper' || key === 'watchdog' ? 'Stopped: last seen ' + ago((now - x.at) * 1000)
        : helperLate ? 'Not checked since the helper stopped (' + ago((now - x.at) * 1000) + ')' : 'Overdue: last seen ' + ago((now - x.at) * 1000);
    }
    // A hot laptop or a low battery is red, but it isn't a routine that stopped working.
    const laptopOnly = !late && ((key === 'temp' && /^Hot/.test(text)) || (key === 'battery' && /^Low battery/.test(text)));
    if (state === 'down' && !laptopOnly) bad++;
    if (state === 'running') busy++;
    if (state === 'waiting') waiting++;
    const when = x && x.last ? 'Last ' + clock(new Date(x.last * 1000)) : '';
    rows.push({ n: name, l: text + (when ? ' · ' + when : ''), dot: DOT[state] || DOT.off, key });
  }
  const names = Object.fromEntries(ROUTINES.concat(beats));
  const incidents = (r.incidents || []).slice(0, 30).map((x) => {
    const mins = Math.max(1, Math.round(((x.back || now) - x.down) / 60));
    const long = mins < 60 ? mins + ' min' : Math.floor(mins / 60) + ' h ' + (mins % 60) + ' min';
    const fixes = (x.fixes || []).map((f) => clock(new Date(f.at * 1000)) + ' ' + f.what).join(' · ');
    return { key: x.id || (x.key + x.down), name: (names[x.key] || x.key) + (x.back ? '' : ' · still down'),
      when: clock(new Date(x.down * 1000)) + ' · ' + long, why: 'Why: ' + (x.why || 'not known') + (fixes ? '. ' + fixes : ''),
      c: x.back ? '#0f172a' : '#b42318' };
  });
  const t = r.temperature, b = r.battery, s = r.stats, lid = r.lidsleep;
  const laptop = [];
  if (t) laptop.push((t.lvl === 'normal' ? 'Cool' : cap(t.lvl)) + (t.cpu != null ? ', ' + Math.round(t.cpu) + '°C' : '') + (t.heat ? ' · ' + t.heat : ''));
  if (b) laptop.push((b.pct != null ? 'Battery ' + b.pct + '%' : 'Battery') + (b.words ? ' · ' + b.words : ''));
  if (lid && lid.words) laptop.push(lid.words);
  const word = bad ? bad + ' not working' : busy || waiting ? 'All working' + (busy ? ' · ' + busy + ' running now' : '') + (waiting ? ' · ' + waiting + ' waiting' : '') : 'All working';
  return { rows, ok: !bad, word, incidents, laptop: laptop.join(' · ') || (r.laptop ? 'No reading yet' : ''), stats: s && s.words ? s.words : '',
    hasLaptop: !!(r.laptop || t || b || lid), hasStats: !!(s && s.words), noLog: !!r.noLog,
    forYou: (r.forYou || []).map((h, k) => ({ key: k, t: (h.who ? cap(h.who) : 'An agent') + '’s helper: ' + h.question })) };
}

// The two bars: the 5-hour limit (when the reading carries one) and the weekly limit.
function usage(u) {
  if (!u) return { bars: [], read: 'No reading yet', stale: false, has: false, op: 1 };
  const age = Date.now() - new Date(u.checkedAt).getTime();
  const stale = age > 20 * 60000 || !u.readable;
  const limits = Array.isArray(u.limits) ? u.limits : [];
  const five = limits.find((l) => /5-hour/i.test(l.label) && (!l.kept || !u.readable));
  const week = limits.find((l) => /^weekly.*all/i.test(l.label)) || limits.find((l) => /^weekly/i.test(l.label) && !/fable/i.test(l.label));
  const bars = [];
  for (const [l, name] of [[five, '5-hour'], [week, 'Weekly']]) {
    if (!l) continue;
    const reset = l.resetsAt && new Date(l.resetsAt).getTime() <= Date.now();
    const kept = l.kept || !u.readable;
    const pct = kept && reset ? 0 : Math.round(l.percent);
    bars.push({ key: name, name, pct, w: Math.min(100, Math.max(0, pct)),
      line: pct + '%' + (l.resetsAt && !reset ? ' · ' + until(l.resetsAt) : reset ? ' · reset, no fresh reading since' : ''),
      c: kept ? '#94a3b8' : '#0f172a', op: kept ? 0.55 : 1 });
  }
  const read = 'Read ' + ago(age) + (u.by ? ' by ' + u.by : '') + (u.from ? ', on ' + u.from : '') + (u.readable ? '' : '. The last reading failed: these are the last known numbers');
  return { bars, read, stale, has: true, op: stale ? 0.5 : 1, now: five && !five.kept ? Math.round(five.percent) : null, week: week ? Math.round(week.percent) : null };
}

// The status block as a timeline: the state, the step, what was just done, what's next, the log.
function working(s) {
  if (!s || s.error) return null;
  const [word, c] = STATE[s.state] || [s.title || s.state || '', '#475569'];
  const steps = (s.current && s.current.steps) || [];
  const mark = (x) => x.mark || x.status;
  const done = steps.filter((x) => mark(x) === 'done').length;
  return {
    word, c, headline: String(s.headline || '').replace(/^Now:\s*/, ''), updated: String(s.updated || ''),
    phase: s.current && s.current.phase ? 'Phase ' + String(s.current.phase).replace(/^Phase\s*/, '') + (steps.length ? ' · ' + done + ' of ' + steps.length + ' steps done' : '') : '',
    pct: steps.length ? Math.round((done / steps.length) * 100) : 0, hasSteps: steps.length > 0,
    notes: (s.notes || []).map((n, i) => ({ key: i, label: n.label, text: n.text })),
    log: (s.log || []).map((l, i) => ({ key: i + ' ' + l.time, t: l.time, text: l.text })), hasLog: (s.log || []).length > 0,
    problems: (s.problems || []).map((p, i) => ({ key: i, t: typeof p === 'string' ? p : p.text || p.why || '' }))
  };
}

// A small Markdown reader for a hand-over: headings, paragraphs, list items, quotes and code,
// as plain text blocks (the template draws each as text, never as HTML).
function blocks(md) {
  const out = []; let para = [], code = null;
  const flush = () => { if (para.length) out.push({ p: true, text: para.join(' ') }); para = []; };
  const plain = (t) => t.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/`([^`]+)`/g, '$1').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1').replace(/(^|\s)[*_]([^*_]+)[*_](?=\s|$|[.,;:])/g, '$1$2');
  for (const raw of String(md || '').split('\n')) {
    if (code) { if (/^```/.test(raw)) { out.push({ code: true, text: code.join('\n') }); code = null; } else code.push(raw); continue; }
    if (/^```/.test(raw)) { flush(); code = []; continue; }
    const line = raw.trimEnd();
    let m;
    if (!line.trim()) { flush(); continue; }
    if ((m = line.match(/^(#{1,6})\s+(.*)$/))) { flush(); out.push({ h: true, big: m[1].length <= 1, text: plain(m[2]) }); continue; }
    if ((m = line.match(/^\s*(?:[-*+]|\d+[.)])\s+(.*)$/))) { flush(); out.push({ li: true, text: plain(m[1]) }); continue; }
    if ((m = line.match(/^>\s?(.*)$/))) { flush(); out.push({ quote: true, text: plain(m[1]) }); continue; }
    if (/^\s*([-*_])\s*\1\s*\1[\s\-*_]*$/.test(line)) { flush(); continue; }
    if (/^\|/.test(line)) { flush(); out.push({ code: true, text: line }); continue; }
    para.push(plain(line.trim()));
  }
  if (code) out.push({ code: true, text: code.join('\n') });
  flush();
  return out.map((b, i) => Object.assign({ key: i, h: false, big: false, p: false, li: false, code: false, quote: false }, b));
}

const MOSCOW = { must: '#c0392b', should: '#d9730d', could: '#2f7fd1', wont: '#7a5aa8' };
function planning(P) {
  if (!P || !Array.isArray(P.groups)) return null;
  const by = Object.fromEntries((P.rows || []).map((r) => [r.label, r]));
  return P.groups.filter((g) => g.labels.length).map((g) => ({
    key: g.tag || 'none', phase: g.name + ' · ' + g.labels.length,
    items: g.labels.map((l) => by[l]).filter(Boolean).map((r) => ({ key: r.label, t: r.title, s: r.label + (r.bug ? ' · bug' : ''), c: MOSCOW[r.moscow] || '#8a94a0', bug: !!r.bug }))
  }));
}

const KIND = { done: ['#16a34a', 'none', 'done'], broken: ['#dc2626', 'none', 'found broken'], running: ['#ca8a04', 'none', 'running now'],
  expected: ['transparent', '1.5px dashed #a16207', 'expected'], you: ['#6d28d9', 'none', 'waits for you'] };
function session(n) {
  if (!n) return null;
  const rows = (n.rows || []).map((r) => Object.assign({}, r, { a: new Date(r.start).getTime(), b: new Date(r.end).getTime() })).filter((r) => r.a && r.b);
  const from = rows.length ? Math.min(...rows.map((r) => r.a)) : 0;
  const to = rows.length ? Math.max(...rows.map((r) => r.b)) : 0;
  const span = Math.max(60000, to - from);
  const done = rows.filter((r) => r.kind === 'done').length, broken = rows.filter((r) => r.kind === 'broken').length;
  return {
    title: n.title + ', ' + dayWords(n.key) + (rows.length ? ', ' + hm(new Date(from)) + ' to ' + hm(new Date(to)) : ''),
    count: rows.length ? done + ' of ' + rows.length + ' done' + (broken ? ', ' + broken + ' found broken' : '') : 'Nothing recorded',
    rows: rows.map((r, i) => {
      const k = KIND[r.kind] || KIND.done;
      return { key: (r.key || r.name) + ' ' + i, name: r.name, state: hm(new Date(r.a)) + '–' + hm(new Date(r.b)) + ' · ' + k[2],
        start: Math.round(((r.a - from) / span) * 1000) / 10, w: Math.max(1.5, Math.round(((r.b - r.a) / span) * 1000) / 10), c: k[0], border: k[1] };
    }),
    axis: rows.length ? [hm(new Date(from)), hm(new Date(from + span / 2)), hm(new Date(to))] : ['', '', ''],
    log: (n.log || []).map((l, i) => ({ key: i, t: hm(new Date(l.at)), text: l.text })), hasLog: (n.log || []).length > 0,
    has: rows.length > 0
  };
}

function updates(u, log, st) {
  if (!u) return null;
  const run = (u.run && u.run.state) || 'idle';
  const recent = (run === 'done' || run === 'failed') && Date.now() / 1000 - ((u.run && u.run.at) || 0) < 1800;
  const busy = run === 'waiting' || run === 'updating';
  const versions = [];
  const seen = new Set();
  const list = (u.available ? (u.new || []).map((s) => Object.assign({}, s, { newer: true })) : []).concat((log && log.versions) || []);
  for (const s of list) {
    const key = s.version || s.title;
    if (seen.has(key)) continue;
    seen.add(key);
    const items = (s.groups || []).flatMap((g) => g.items);
    versions.push({ key, v: s.coming ? 'Coming next' : 'v' + s.version, tag: s.newer ? 'New, not installed yet' : s.version === u.version ? 'You’re here' : s.coming ? 'Not in a version yet' : '',
      tc: s.version === u.version ? '#15803d' : '#475569', line: items.join(' ') });
  }
  if (!seen.has(u.version)) versions.unshift({ key: u.version, v: 'v' + u.version, tag: 'You’re here', tc: '#15803d', line: u.ahead ? 'This copy has ' + u.ahead + ' change' + (u.ahead === 1 ? '' : 's') + ' that aren’t in a version yet.' : '' });
  const now = busy ? 'Updating to v' + ((u.run && u.run.to) || u.latest)
    : u.available ? 'A newer version is out: v' + u.latest + '.'
    : u.latest && !u.offline ? 'You’re on the latest version, v' + u.version + '.'
    : u.offline ? 'Couldn’t look for a newer version just now.' : 'Not checked for a newer version yet.';
  return {
    versions, now, idle: !busy && !recent, busy, done: recent && run === 'done', failed: recent && run === 'failed', available: !!u.available,
    label: u.available ? 'Update to v' + u.latest : 'Check now', step: busy ? [u.run.step, u.run.message].filter(Boolean).join(' · ') || 'Getting the new version…' : '',
    message: (u.run && u.run.message) || '', checkLabel: st.mpUpdBusy ? 'Checking…' : 'Check now',
    sub: busy ? 'updating…' : u.available ? 'v' + u.latest + ' is out' : u.latest && !u.offline ? 'you’re on the latest' : 'you’re on v' + u.version, said: st.mpUpdSaid || ''
  };
}

// ---- the demo, in the same shape -------------------------------------------------------

function demoModel(st, D) {
  return {
    working: { word: D.working[0].state, c: '#ca8a04', headline: D.working[0].name, updated: '', phase: D.working[1].name + ' · ' + D.working[1].state, pct: D.working[0].pct, hasSteps: true,
      notes: [], log: [], hasLog: false, problems: [] },
    health: { rows: D.routines.map((r) => ({ n: r.n, l: r.l, dot: '#16a34a', key: r.n })), ok: true, word: 'All working', laptop: 'Cool · battery 82% · keeps working with the lid closed', stats: '', hasLaptop: true, hasStats: false, noLog: false, forYou: [],
      incidents: [{ key: 'a', name: 'Mail check stopped', when: 'Monday · 12 min', why: 'The mail server timed out. It restarted itself and caught up.', c: '#0f172a' },
        { key: 'b', name: 'Calendar sync was slow', when: 'Last week · 40 min', why: 'Google answered slowly. Nothing was lost.', c: '#0f172a' }] },
    usage: { bars: [{ key: '5', name: '5-hour', pct: 34, w: 34, line: '34% · resets 18:10', c: '#0f172a', op: 1 }, { key: 'w', name: 'Weekly', pct: 61, w: 61, line: '61% · resets Monday', c: '#0f172a', op: 1 }], read: '', stale: false, has: true, op: 1 },
    planning: D.planning.map((p) => ({ key: p.phase, phase: p.phase, items: p.items.map((i) => ({ key: i.t, t: i.t, s: i.s, c: i.c, bug: false })) })),
    handovers: D.handovers.map((h, i) => ({ key: h.name, name: h.name, meta: h.meta, mc: h.mc, i })),
    session: { title: 'Today, 10:00 to now', count: '2 of 3 done', rows: D.sessions.map((r) => Object.assign({ key: r.name }, r)), axis: ['10:00', '12:00', '14:20'], log: [], hasLog: false, has: true },
    days: [{ key: 'tue', name: 'Tuesday', meta: '4 done', pick: () => {} }, { key: 'mon', name: 'Monday', meta: '3 done, 1 found broken', pick: () => {} }],
    updates: { versions: [{ key: '4.2', v: 'v4.2', tag: 'You’re here', tc: '#15803d', line: 'Bucketlist items can hold items of their own.' }, { key: '4.3', v: 'v4.3', tag: 'Coming next', tc: '#475569', line: 'Calendar clean-up.' }],
      now: '', idle: st.updating === 0, busy: st.updating === 1, done: st.updating === 2, failed: false, available: true, label: D.update.labels[st.updating], step: D.update.labels[1],
      message: '', checkLabel: 'Check now', sub: 'you’re on the latest', said: '' }
  };
}

const errLine = 'This couldn’t be read just now.';

export const card = (st, D) => {
  if (D === demo) return D.card;
  const h = (D.handovers && D.handovers.handovers) || [];
  const top = h[0];
  const hl = health(D.routines);
  const running = hl && !hl.ok ? hl.word + '.' : 'Everything is running.';
  if (top && dayWords(top.date) === 'today') return { kicker: 'New hand-over', headline: top.title, sub: 'Ready for you and Claude Code', line: running + ' A hand-over is waiting for you.' };
  const w = working(D.status);
  return { kicker: 'Status', headline: hl && !hl.ok ? hl.word : 'Everything is running', sub: w ? w.word + (w.headline ? ': ' + w.headline : '') : '', line: running };
};

export function vals(st, ctx, D) {
  const { app } = ctx;
  const isDemo = D === demo;
  // The prototypes' own values, for the demo (and its equivalence check).
  const proto = isDemo ? {
    handovers: D.handovers.map((h) => Object.assign({}, h, { open: () => app.go('handover') })),
    working: D.working, planning: D.planning, sessionRows: D.sessions, routines: D.routines,
    updLabel: D.update.labels[st.updating], updIdle: st.updating === 0, updBusy: st.updating === 1, updDone: st.updating === 2,
    startUpdate: () => { app.setState({ updating: 1 }); setTimeout(() => app.setState({ updating: 2 }), D.update.takesMs); },
    reload: () => { app.setState({ updating: 0 }); app.say(D.update.doneSay); }
  } : {};

  let m, rows, homeLines;
  const err = (!isDemo && D.err) || {};
  if (isDemo) {
    m = demoModel(st, D);
    rows = D.rows; homeLines = D.homeLines;
  } else {
    const hl = health(D.routines), us = usage(D.usage);
    const hs = (D.handovers && D.handovers.handovers) || [];
    const sess = (D.sessions && D.sessions.sessions) || [];
    const pick = st.mpSession || (sess.find((x) => x.rows > 0) || sess[0] || {}).key;
    const day = pick && D.days && D.days[pick];
    const newCount = hs.filter((h) => dayWords(h.date) === 'today').length;
    m = {
      working: working(D.status), health: hl, usage: us, planning: planning(D.planning),
      handovers: hs.map((h, i) => ({ key: h.name, name: h.title, meta: dayWords(h.date) === 'today' ? 'New · today' : 'Prepared ' + dayWords(h.date), mc: dayWords(h.date) === 'today' ? '#854d0e' : '#475569', i })),
      session: session(day),
      days: sess.map((s) => ({ key: s.key, name: s.title + ', ' + dayWords(s.key), meta: (s.rows ? s.rows + ' recorded' : 'nothing recorded') + (s.key === pick ? ' · shown above' : ''), pick: () => openSession(app, s.key) })),
      updates: updates(D.update, D.changelog, st)
    };
    // Her space's rows, and her lines on home.
    const calls = ((D.calls && D.calls.calls) || []).filter((c) => /moneypenny/i.test(c.agent || ''));
    const texts = (D.team && D.team.messages) || [];
    const lastText = texts.length ? new Date(texts[texts.length - 1].at * 1000) : null;
    rows = [
      ['Hand-overs', hs.length ? (newCount ? newCount + ' new' : String(hs.length)) : (D.handovers ? 'None yet' : ''), 'handovers'],
      ['Her notes', '', 'notes'],
      ['Texts', lastText ? cap(dayWords(lastText.toISOString().slice(0, 10))) : '', ['chat', { chatAgent: 'mp' }]],
      ['Past calls', calls.length ? cap(calls[0].date ? dayWords(calls[0].date) : calls[0].started) : '', 'pastCalls']
    ];
    homeLines = [];
    if (hl) homeLines.push({ t: hl.ok ? 'Everything is running' : hl.word, c: hl.ok ? '#15803d' : '#b42318', w: '600' });
    if (us.has && (us.now != null || us.week != null)) homeLines.push({ t: 'Usage: ' + [us.now != null ? us.now + '% now' : '', us.week != null ? us.week + '% this week' : ''].filter(Boolean).join(', '), c: us.stale ? '#94a3b8' : '#0f172a', w: '400' });
    if (m.working) homeLines.push({ t: m.working.word + (m.working.headline ? ': ' + m.working.headline : ''), c: '#0f172a', w: '400' });
  }

  const U = m.updates;
  const startUpdate = isDemo ? proto.startUpdate : async () => {
    // Update only when the server says a newer version is out; otherwise the button is Check now.
    app.setState({ mpUpdBusy: true, mpUpdSaid: '' });
    try {
      const u = await app.api.post(U && U.available ? 'api/update/start' : 'api/update/check', {}, 'update');
      put(app, { update: u, err: { update: '' } });
      app.setState({ mpUpdBusy: false });
      pollUpdate(app);
    } catch (e) { app.setState({ mpUpdBusy: false, mpUpdSaid: 'That didn’t go through. Try again in a minute.' }); }
  };
  const check = isDemo ? () => {} : async () => {
    app.setState({ mpUpdBusy: true, mpUpdSaid: '' });
    try { put(app, { update: await app.api.post('api/update/check', {}, 'update'), err: { update: '' } }); app.setState({ mpUpdBusy: false }); }
    catch (e) { app.setState({ mpUpdBusy: false, mpUpdSaid: 'Couldn’t look just now. Try again in a minute.' }); }
  };
  // Turn everything on: the Mac app's own button (the status server's /hq/fix): starts what is
  // off, never stops or restarts anything that runs.
  const turnOn = isDemo ? () => app.say('Everything is on') : async () => {
    try {
      const out = await app.api.post('status/hq/fix', {}, 'fix');
      const ok = ((out && out.fixed) || []).filter((f) => f.ok).map((f) => f.what);
      const bad = ((out && out.fixed) || []).filter((f) => f.ok === false).map((f) => f.what);
      app.say((ok.length ? ok.join(', ') : 'Nothing was off') + (bad.length ? '; couldn’t do: ' + bad.join(', ') : ''));
    } catch (e) { app.say('That didn’t go through. Try again in a minute.'); }
    setTimeout(() => read(app, 'routines'), 1500);
  };

  // One hand-over, read as text.
  const hName = isDemo ? null : st.mpHandover;
  const hText = hName && D.texts && D.texts[hName];
  const hMeta = !isDemo && ((D.handovers && D.handovers.handovers) || []).find((h) => h.name === hName);
  const B = (kind, text, key) => Object.assign({ key, h: false, big: false, p: false, li: false, code: false, quote: false, text }, { [kind]: true });
  let handover;
  if (isDemo) {
    handover = { kicker: 'New · prepared today', title: 'Calendar clean-up', sub: 'Ready for you and Claude Code to build.', loading: false, failed: false, has: true,
      blocks: [B('h', 'What she prepared', 0), B('p', 'Birthdays show twice when two calendars hold them. She lists where it happens, what to keep, and a test to prove it’s gone.', 1)],
      meta: '3 parts · about 40 minutes of work' };
  } else {
    const bl = hText ? blocks(hText.text) : [];
    // Its own title is its first heading: shown on top, not twice.
    if (bl.length && bl[0].h && hText && bl[0].text.trim() === String(hText.title || '').trim()) bl.shift();
    handover = { kicker: hMeta ? (dayWords(hMeta.date) === 'today' ? 'New · prepared today' : 'Prepared ' + dayWords(hMeta.date)) : '',
      title: (hText && hText.title) || (hMeta && hMeta.title) || '', sub: 'For you and Claude Code.', blocks: bl,
      meta: hText && hText.bytes ? 'About ' + Math.max(1, Math.round(hText.bytes / 1500)) + ' min to read' : '',
      loading: !!hName && !hText && !err['handover:' + hName], failed: !hText && !!err['handover:' + hName], has: !!hText };
  }

  const H = m.health;
  const mpv = {
    status: m.working || { word: '', c: '', headline: '', updated: '', phase: '', pct: 0, hasSteps: false, notes: [], log: [], hasLog: false, problems: [] },
    hasStatus: !!m.working, statusWait: !isDemo && !m.working, statusWord: err.status ? errLine : 'Looking…', statusFailed: !isDemo && !m.working && !!err.status,
    health: H || { rows: [], ok: true, word: '', incidents: [], laptop: '', stats: '', hasLaptop: false, hasStats: false, forYou: [] },
    hasHealth: !!H, healthWait: !isDemo && !H, healthWord: err.routines ? errLine : 'Looking…', healthFailed: !isDemo && !H && !!err.routines,
    banner: H ? (H.ok ? { t: 'Everything is running', bg: '#f0fdf4', dot: '#16a34a', fg: '#14532d' } : { t: H.word, bg: '#fef2f2', dot: '#dc2626', fg: '#7f1d1d' })
      : { t: err.routines ? 'Health couldn’t be read just now' : 'Looking…', bg: '#f8fafc', dot: '#94a3b8', fg: '#475569' },
    noIncidents: !!H && !H.incidents.length, incidentsWord: H && H.noLog ? 'No incident log yet: HQ was just installed.' : 'Nothing has gone down since the log started.',
    usage: m.usage, hasBars: m.usage.bars.length > 0, noBars: !m.usage.bars.length,
    usageWord: !isDemo && err.usage ? errLine : 'No reading yet. A call or a chat fills it in.', hasRead: !!m.usage.read && m.usage.has,
    planning: m.planning || [], planningWait: !isDemo && !m.planning, planningWord: err.planning ? errLine : 'Looking…', planningFailed: !isDemo && !m.planning && !!err.planning,
    planningEmpty: !!m.planning && !m.planning.length,
    handovers: m.handovers.map((h) => Object.assign({}, h, { open: isDemo ? () => app.go('handover') : () => openHandover(app, h.key) })),
    handoversWait: !isDemo && !D.handovers, handoversWord: err.handovers ? errLine : 'Looking…', handoversFailed: !isDemo && !D.handovers && !!err.handovers,
    handoversEmpty: !isDemo && !!D.handovers && !m.handovers.length,
    handover, openAgain: () => hName && openHandover(app, hName),
    session: m.session || { title: '', count: '', rows: [], axis: ['', '', ''], log: [], hasLog: false, has: false },
    hasSession: !!(m.session && m.session.has), sessionEmpty: !isDemo && !!m.session && !m.session.has,
    sessionWait: !isDemo && !!st.mpSession && !m.session, sessionWord: err['session:' + st.mpSession] ? errLine : 'Looking…',
    days: m.days, daysWait: !isDemo && !D.sessions, daysWord: err.sessions ? errLine : 'Looking…', daysFailed: !isDemo && !D.sessions && !!err.sessions,
    updates: U || { versions: [], now: '', idle: false, busy: false, done: false, failed: false, available: false, label: '', step: '', message: '', checkLabel: 'Check now', sub: '', said: '' },
    hasUpdates: !!U, updatesWait: !isDemo && !U, updatesWord: err.update ? errLine : 'Looking…', updatesFailed: !isDemo && !U && !!err.update,
    updateBtn: startUpdate, checkNow: check, reloadPage: isDemo ? proto.reload : () => { if (typeof location !== 'undefined') location.reload(); },
    updateSub: U ? U.sub : '', healthSub: H ? H.word.toLowerCase() : 'routines, the laptop, incidents',
    turnOn,
    retry: isDemo ? () => {} : () => load(app)
  };

  return {
    agent: { mp: { homeLines, rows } },
    sheets: {},
    titles: {},
    values: Object.assign(proto, { mpv })
  };
}
