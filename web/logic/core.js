// The core: what belongs to no single area. The screens and moving between them, the
// three agents (names, roles, colours), the design and device in use, home and the
// three spaces' fronts, the toast and the sheet.
//
// How an area module (logic/<area>.js) works; app.js gathers them, WIRING.md has more:
// - NAME, start (its state at the start), vals(st, ctx, D) -> { values, agent, sheets,
//   titles, submit }. D is where its data comes from: the demo module, or state.data.NAME.
// - WIRED = false until the area reads real data. Not wired, or in demo mode (?demo=1 or
//   localStorage hq-demo = 1), D is the area's demo module (export { demo }); wired, D is
//   state.data.NAME, put there with app.setData(NAME, ...). While that is still missing
//   the area's vals isn't called (its holes stay empty, so the template shows its own empty
//   state or nothing), unless the area exports LOADING_OK = true and handles D == null.
// - load(app): fetch its data; called once at mount and again when the app comes back to
//   the foreground or online. enter: { screen: (app) => ... }: called when that screen is
//   opened, for data that must be fresh then. Both only for a wired area outside demo mode.
// - Talk to the server only through app.api (web/api.js): get(path), post(path, body, tag).

import { typedIn } from '../engine.js';

// The three designs one app carries.
export const DESIGNS = [
  { id: 'spotlight', name: 'Spotlight', line: 'One of the three at a time, swipe between them' },
  { id: 'thread', name: 'Thread', line: 'HQ as three conversations' },
  { id: 'desk', name: 'Desk', line: 'The three side by side, today underneath' }
];

// The three agents. Their card text (kicker, headline, sub, line) comes from their area.
export const AGENTS = {
  donna: { key: 'donna', name: 'Donna', initial: 'D', role: 'Your personal secretary', color: '#6d28d9', ink: '#ffffff', tint: '#f5f3ff', accent: '#6d28d9', ring: 'rgba(109,40,217,0.18)' },
  pepper: { key: 'pepper', name: 'Pepper', initial: 'P', role: 'Your life coach', color: '#c2410c', ink: '#ffffff', tint: '#fff3ec', accent: '#c2410c', ring: 'rgba(194,65,12,0.18)' },
  mp: { key: 'mp', name: 'Moneypenny', initial: 'M', role: 'Your head of the development team', color: '#ca8a04', ink: '#0f172a', tint: '#fefce8', accent: '#854d0e', ring: 'rgba(202,138,4,0.22)' }
};
export const ORDER = ['donna', 'pepper', 'mp'];
// Donna's space rows and home lines come from several areas, each keyed; this is their order.
const KEYED_ORDER = {
  rows: ['agenda', 'mail', 'todo', 'lists', 'notes', 'pastCalls', 'texts'],
  homeLines: ['nudges', 'mail', 'todo']
};
// An agent's rows or home lines: a list as given, or the keyed pieces in their order.
function inOrder(kind, v) {
  if (!v) return [];
  if (Array.isArray(v)) return v;
  const known = KEYED_ORDER[kind].filter((k) => k in v);
  return known.concat(Object.keys(v).filter((k) => !known.includes(k))).map((k) => v[k]);
}
const SPACES = ['donna', 'pepper', 'mp'];

// Every sub-screen (shown under the shared header with a back button).
export const SUBS = ['agenda', 'appt', 'todo', 'todoItem', 'lists', 'bucketItem', 'mail', 'notes', 'pastCalls', 'callLog', 'map', 'checkin', 'game', 'handovers', 'handover', 'status', 'planning', 'sessions', 'health', 'updates', 'settings', 'weather', 'tutorial', 'todoList', 'agendaFilter', 'kinds', 'subItem', 'layer', 'games', 'features', 'sound', 'voices'];
// Every screen there is.
export const SCREENS = ['home', 'donna', 'pepper', 'mp', 'call', 'transcript', 'chat'].concat(SUBS);

const TITLES = { agenda: 'Agenda', todo: 'To-do', todoItem: 'To-do', lists: 'Lists', mail: 'Mail', notes: 'Notes', pastCalls: 'Past calls', callLog: 'A past call',
  map: 'The map', checkin: 'Check-ins', game: 'The six-week game', handovers: 'Hand-overs', handover: 'Hand-over', status: 'Status', planning: 'The planning board', sessions: 'Work sessions', health: 'Health', updates: 'Updates', settings: 'Settings', tutorial: 'Tutorial',
  agendaFilter: 'Show in the agenda', kinds: 'Kinds of time', games: 'Your games', features: 'What HQ helps you with', sound: 'Microphone and sound', voices: 'Voices' };

export const start = { screen: 'home', stack: [], space: 'donna', design: 'desk', toast: null, toastUndo: false, sheet: null, drafts: {} };

// A text box with a draft in state: value="{{ drafts.NAME }}" onInput="{{ typed.NAME }}"
// onKeyDown="{{ enter.NAME }}". Enter hands the text to the area's submit.NAME and clears it.
// A keystroke keeps the draft in state without a render (the box already shows what he
// typed). The draft is written into the drafts object in place, so a handler made by the last
// render that reads st.drafts still sees what is in the box.
function boxes(st, app, submit) {
  const typed = {}, enter = {};
  for (const name of Object.keys(submit)) {
    typed[name] = (e) => app.keepDraft(name, e.target);
    enter[name] = (e) => {
      if (e.key !== 'Enter' || e.isComposing) return;
      const text = (e.target.value || '').trim();
      if (!text) return;
      e.preventDefault();
      e.target.value = '';
      typedIn(e.target);
      app.setState((x) => ({ drafts: Object.assign({}, x.drafts, { [name]: '' }) }));
      submit[name](text);
    };
  }
  return { drafts: st.drafts, typed, enter };
}

// Installed on the app.
export const methods = {
  // A text box's draft, kept without a render (see boxes).
  keepDraft(name, node) {
    if (!this.state.drafts) this.state = Object.assign({}, this.state, { drafts: {} });
    this.state.drafts[name] = node.value;
    typedIn(node);
  },
  // Change state without a render: for what a text box holds while he types. node is the box,
  // so a later render neither writes the same text back nor misses a clear.
  quietState(update, node) {
    const p = typeof update === 'function' ? update(this.state, this.props) : update;
    if (p) this.state = Object.assign({}, this.state, p);
    if (node) typedIn(node);
  },
  go(screen, extra) {
    this.setState((st) => Object.assign({ screen, stack: st.stack.concat([st.screen]) }, extra || {}));
    if (this.entered) this.entered(screen);
  },
  back() {
    this.setState((st) => {
      const stack = st.stack.slice();
      const prev = stack.length ? stack.pop() : 'home';
      return { screen: prev, stack, confirmHang: false };
    });
  },
  // A short line at the bottom. With undoFn the toast shows Undo, which runs it and clears the
  // toast; without one there's no Undo. In demo mode the prototypes' own rule decides (their words).
  say(t, undoFn) {
    const fn = typeof undoFn === 'function' ? undoFn : null;
    this._undo = fn;
    this.setState({ toast: t, toastUndo: this.demoMode ? /^(Ticked|Moved|Let go|Note cleared|Deleted|“)|is back on/.test(t) : !!fn });
    clearTimeout(this._t);
    this._t = setTimeout(() => { this._undo = null; this.setState(this.demoMode ? { toast: null } : { toast: null, toastUndo: false }); }, fn ? 8000 : 4000);
  },
  undoToast() {
    const fn = this._undo;
    this._undo = null;
    clearTimeout(this._t);
    this.setState({ toast: null, toastUndo: false });
    if (fn) Promise.resolve().then(fn).catch((err) => console.error('HQ: undo', err));
  }
};

// The agents as this workspace has them (/api/agents, read by the call area): a workspace can
// rename them, give them another colour, or say differently what each is for. The design's
// values stay where the server says nothing.
const SERVER_ID = { donna: 'donna', pepper: 'pepper', mp: 'moneypenny' };
function hex(c) { const m = /^#?([0-9a-f]{6})$/i.exec(String(c || '')); return m ? [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16)) : null; }
function mix(rgb, w, to) { return '#' + rgb.map((v) => Math.round(v * (1 - w) + to * w).toString(16).padStart(2, '0')).join(''); }
const ownCache = { src: null, out: null };
function ownAgents(st) {
  const list = st.data && st.data.call && st.data.call.agents;
  if (!list) return null;
  if (ownCache.src === list) return ownCache.out;
  const out = {};
  for (const k of ORDER) {
    const a = list[k];
    if (!a) continue;
    const o = {};
    if (a.name && a.name !== AGENTS[k].name) { o.name = a.name; o.initial = a.name.trim().charAt(0).toUpperCase(); }
    if (a.speciality) o.role = a.speciality;
    const rgb = hex(a.colour);
    if (rgb && a.colour.toLowerCase() !== AGENTS[k].color.toLowerCase()) {
      const lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255;
      Object.assign(o, { color: a.colour, ink: lum > 0.6 ? '#0f172a' : '#ffffff', tint: mix(rgb, 0.93, 255), accent: lum > 0.6 ? mix(rgb, 0.45, 0) : a.colour,
        ring: 'rgba(' + rgb.join(',') + ',0.2)' });
    }
    out[k] = o;
  }
  ownCache.src = list; ownCache.out = out;
  return out;
}

// What every area gets: the app, the agents with their cards, the screen and its flags.
export function context(st, app, cards) {
  const AG = {};
  const own = app.demoMode ? null : ownAgents(st);
  for (const k of ORDER) AG[k] = Object.assign({}, AGENTS[k], (own && own[k]) || {}, cards[k] || {});
  const sc = st.screen;
  const s = { home: sc === 'home', inner: sc !== 'home', herView: sc === 'home' || SPACES.indexOf(sc) >= 0, space: SPACES.indexOf(sc) >= 0,
    donna: sc === 'donna', pepper: sc === 'pepper', mp: sc === 'mp', call: sc === 'call', transcript: sc === 'transcript', chat: sc === 'chat', sub: SUBS.indexOf(sc) >= 0 };
  SUBS.forEach((k) => { s[k] = sc === k; });
  const sa = Object.assign({}, AG[st.space]);
  // Pepper's and Moneypenny's button under their card: a card can hide it (actionOn false) or
  // say what it does (act); the design's own goes to the check-ins and the hand-over.
  sa.hasAction = st.space !== 'donna' && sa.actionOn !== false;
  sa.action = typeof sa.act === 'function' ? () => sa.act(app) : st.space === 'pepper' ? () => app.go('checkin') : () => app.go('handover');
  sa.actionLabel = st.space === 'pepper' ? 'Start the check-in' : 'Read the hand-over';
  return { app, AG, sc, s, sa, device: app.device };
}

// The core's render values, given the areas' parts: per agent its home lines and space rows,
// the sheets each area opens, the titles each area gives its screens, and what each of
// its text boxes does with the text on Enter (submit).
const pad2 = (n) => String(n).padStart(2, '0');
const hhmm = (d) => pad2(d.getHours()) + ':' + pad2(d.getMinutes());
const WEEKDAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const lowFirst = (t) => (t ? t.charAt(0).toLowerCase() + t.slice(1) : '');
// When a text was sent, short: 14:02 today, else the weekday, else the date.
function sentWhen(at) {
  const d = new Date(at * 1000), now = new Date();
  const days = Math.round((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 864e5);
  if (days === 0) return hhmm(d);
  if (days === 1) return 'yesterday';
  if (days < 7) return WEEKDAYS[d.getDay()];
  return d.getDate() + ' ' + MONTHS[d.getMonth()].slice(0, 3);
}

// The words on home, in the spaces and in the shells that come from several areas or the clock:
// the date, the weather chip, the cards of the Desk phone home, Moneypenny's Status card, the
// incoming call, the mini bar's time, Thread's labels. In demo mode the design's own words.
function shellWords(st, ctx, parts, V) {
  const { app, AG, sa } = ctx;
  const mpv = V.mpv || {};
  const bars = ((mpv.usage && mpv.usage.bars) || []).map((b) => ({ key: b.key || b.name, label: b.name + ' usage', line: b.line, pct: b.pct + '%', w: b.w + '%', op: b.op == null ? 1 : b.op }));
  const hl = (k) => inOrder('homeLines', (parts.agent[k] || {}).homeLines);
  const ring = st.cRing ? AG[st.cRing.agent] || AG.donna : AG.donna;
  const halo = (a) => (a.ring || 'rgba(109,40,217,0.18)').replace(/[\d.]+\)$/, '0.15)');
  const ringBase = { name: ring.name, initial: ring.initial, color: ring.color, ink: ring.ink, tint: ring.tint, halo: halo(ring), title: ring.name + ' is calling' };
  // the Desk phone home's three cards, in their order
  const cards = (c) => ORDER.map((k) => Object.assign({ key: k, open: () => app.go(k, { space: k }) }, c[k]));
  const banner = mpv.banner || { t: '' };
  if (app.demoMode) {
    const out = {
      day: 'Thursday 26', dayLong: 'Thursday 26 November', wxLong: '7° · rain from 16:00', wxDay: 'Thursday · 7° and rain from 16:00',
      nowAt: 'now 14:20', anyTime: 'Any time: renew your passport · pay the parking fine', since: ' This is from 14:02.',
      c: {
        donna: { name: AG.donna.name, initial: AG.donna.initial, color: AG.donna.color, ink: AG.donna.ink, badge: '1 important mail', badgeC: '#b42318', badgeW: '600', dot: false, dotC: '', headline: 'Dentist at 15:00', sub: 'Leave at 14:40 · ' + V.nudgeCount + ' nudges' },
        pepper: { name: AG.pepper.name, initial: AG.pepper.initial, color: AG.pepper.color, ink: AG.pepper.ink, badge: 'Day 12 of the game', badgeC: '#64748b', badgeW: '400', dot: false, dotC: '', headline: 'Weekly check-in', sub: 'Due at 17:00 · about 15 minutes' },
        mp: { name: AG.mp.name, initial: AG.mp.initial, color: AG.mp.color, ink: AG.mp.ink, badge: 'All running', badgeC: '#15803d', badgeW: '600', dot: true, dotC: '#16a34a', headline: 'Calendar clean-up', sub: 'New hand-over for you and Claude Code' }
      },
      st: { word: 'Everything is running', upper: 'EVERYTHING IS RUNNING', fg: '#15803d', dot: '#16a34a' },
      bars, workLine: '2 things being worked on', statusLine: 'Usage 34% now, 61% this week · 2 things being worked on',
      threadHead: 'Today', lastLabel: sa.name + ' · 14:02', hasLast: true,
      ring: Object.assign(ringBase, { name: 'Donna', initial: 'D', color: '#6d28d9', ink: '#ffffff', tint: '#f5f3ff', halo: 'rgba(109,40,217,0.15)', title: 'Donna is calling', line: 'About the dentist: it’s nearly time to leave.' }),
      miniTime: ''
    };
    out.cards = cards(out.c);
    return out;
  }
  const now = new Date(st.clockNow || Date.now());
  const W = V.setv && V.setv.weather && V.setv.weather.ready ? V.setv.weather : null;
  const soon = W && W.hasBars && /^Rain from about (\d\d:\d\d)/.exec(W.radar || '');
  const wet = W && /^Raining now/.test(W.radar || '');
  const chip = V.wxChip || '';
  const rainWords = soon ? 'rain from ' + soon[1] : wet ? 'raining now' : '';
  // Donna's nudges, for "Any time" on the Desk Mac home and her card's line on the Desk phone.
  const nudges = Array.isArray(V.nudges) ? V.nudges : [];
  const mailLine = (hl('donna').find((l) => /mail/.test(l.t || '')) || {}).t || '';
  const nN = nudges.length;
  const pLine = hl('pepper')[0];
  const ok = !banner.t || banner.t === 'Everything is running';
  const healthy = !!(mpv.hasHealth && ok);
  const workLine = (hl('mp').find((l) => !/^Usage|^Everything is running/.test(l.t || '') && l.t !== banner.t) || {}).t || '';
  const usageLine = (hl('mp').find((l) => /^Usage/.test(l.t || '')) || {}).t || '';
  // Thread: the conversation's first day under its heading, and her last text's time under the bubbles.
  const line = st.data && st.data.texts && st.data.texts.lines && st.data.texts.lines[st.space];
  const msgs = line && Array.isArray(line.msgs) ? line.msgs.filter((m) => !m.quiet) : [];
  const firstToday = !msgs.length || sentWhen(msgs[0].at).indexOf(':') > 0;
  const hers = msgs.filter((m) => m.from !== 'me').slice(-1)[0];
  const secs = st.cs === 'live' && st.cStarted ? Math.max(0, Math.floor(((st.cNow || Date.now()) - st.cStarted) / 1000)) : -1;
  const c = (k, badge, badgeC, badgeW, dot, dotC) => ({ name: AG[k].name, initial: AG[k].initial, color: AG[k].color, ink: AG[k].ink, badge, badgeC, badgeW, dot, dotC,
    headline: AG[k].headline || '', sub: AG[k].sub || '' });
  // her card's when ("in 40 minutes", "friday at 01:00") goes first: the Desk phone card shows no kicker
  const when = String(AG.donna.kicker || '').replace(/^Next(\s·\s)?/, '');
  const dsub = [when ? when.charAt(0).toUpperCase() + when.slice(1) : '', AG.donna.sub, nN ? nN + (nN === 1 ? ' nudge' : ' nudges') : ''].filter(Boolean).join(' · ');
  const real = {
    day: WEEKDAYS[now.getDay()] + ' ' + now.getDate(), dayLong: WEEKDAYS[now.getDay()] + ' ' + now.getDate() + ' ' + MONTHS[now.getMonth()],
    wxLong: [chip, rainWords].filter(Boolean).join(' · '), wxDay: WEEKDAYS[now.getDay()] + (chip ? ' · ' + chip + (rainWords ? ' and ' + rainWords : '') : ''),
    nowAt: 'now ' + hhmm(now),
    anyTime: nN ? 'Any time: ' + nudges.map((n) => lowFirst(n.title)).join(' · ') : '',
    since: app.api && app.api.lastOk ? ' This is from ' + hhmm(new Date(app.api.lastOk)) + '.' : '',
    c: {
      donna: Object.assign(c('donna', mailLine, '#b42318', '600', false, ''), { sub: dsub }),
      pepper: c('pepper', pLine ? pLine.t : (AG.pepper.kicker || ''), pLine && pLine.c && pLine.c !== '#0f172a' ? pLine.c : '#64748b', pLine ? pLine.w || '400' : '400', false, ''),
      mp: c('mp', mpv.hasHealth ? (healthy ? 'All running' : banner.t) : '', healthy ? '#15803d' : '#b42318', '600', !!mpv.hasHealth, healthy ? '#16a34a' : '#dc2626')
    },
    st: { word: banner.t, upper: String(banner.t || '').toUpperCase(), fg: mpv.hasHealth ? (healthy ? '#15803d' : '#b42318') : '#475569', dot: banner.dot || '#94a3b8' },
    bars, workLine, statusLine: [usageLine, workLine].filter(Boolean).join(' · '),
    threadHead: firstToday ? 'Today' : '', lastLabel: hers ? sa.name + ' · ' + sentWhen(hers.at) : '', hasLast: !!hers,
    ring: Object.assign(ringBase, { line: st.cRing ? 'About the call you agreed.' : '' }),
    miniTime: secs >= 0 ? ' · ' + pad2(Math.floor(secs / 60)) + ':' + pad2(secs % 60) : ''
  };
  real.cards = cards(real.c);
  return real;
}

export function vals(st, ctx, parts, V) {
  V = V || {};
  const { app, AG, sc, s, sa } = ctx;
  const nav = {};
  SUBS.concat(['call']).forEach((k) => { nav[k] = () => app.go(k); });
  const open = { donna: () => app.go('donna', { space: 'donna' }), pepper: () => app.go('pepper', { space: 'pepper' }), mp: () => app.go('mp', { space: 'mp' }) };

  const R = (r) => {
    const [label, value, to, vc, vw] = r;
    const goTo = Array.isArray(to) ? () => app.go(to[0], to[1]) : () => app.go(to);
    return { label, value, go: goTo, vc: vc || '#475569', vw: vw || '400' };
  };
  const spaceRows = inOrder('rows', (parts.agent[st.space] || {}).rows).map(R);
  const homeLines = (k) => inOrder('homeLines', (parts.agent[k] || {}).homeLines);

  // Whose a sub-screen is, for the small label over its title
  const owner = s.status || s.planning || s.sessions || s.health || s.updates || s.handovers || s.handover ? AG.mp
    : (s.map || s.checkin || s.game ? AG.pepper : (s.settings || s.weather || s.tutorial ? null : AG[st.space]));
  const ownerOut = owner ? { label: owner.name, accent: owner.accent } : { label: 'HQ', accent: '#475569' };
  const titles = Object.assign({}, TITLES, parts.titles);

  const idx = ORDER.indexOf(st.space);
  const homeCards = ORDER.map((k) => Object.assign({}, AG[k], { lines: homeLines(k), call: () => app.startCall(k), open: () => app.go(k, { space: k }) }));
  const rail = ORDER.map((k) => {
    const on = sc !== 'home' && st.space === k;
    return { name: AG[k].name, initial: AG[k].initial, color: AG[k].color, ink: AG[k].ink, line: AG[k].rail || AG[k].headline, current: on ? 'true' : 'false', currentSpot: st.space === k ? 'true' : 'false',
      open: () => app.go(k, { space: k }), pick: () => app.setState({ space: k, screen: 'home', stack: [] }),
      bg: on ? AG[k].tint : '#ffffff', shadow: on ? '0 0 0 2px ' + AG[k].color + ' inset' : '0 0 0 1px #e2e8f0 inset', spotRing: st.space === k ? AG[k].color : 'transparent' };
  });
  const spotDots = ORDER.map((k) => ({ w: k === st.space ? '24px' : '8px', c: AG[k].color, op: k === st.space ? 1 : 0.4 }));
  const sh = st.sheet ? parts.sheets[st.sheet] : null;

  return Object.assign(boxes(st, app, parts.submit), {
    s, nav, open, back: () => app.back(), sa,
    owner: (sc === 'layer' || sc === 'games') ? { label: AG.pepper.name, accent: AG.pepper.accent } : (['features', 'sound', 'voices'].indexOf(sc) >= 0 ? { label: 'Settings', accent: '#475569' } : ownerOut),
    title: titles[sc] || '',
    spaceRows, home: () => app.setState({ screen: 'home', stack: [] }), homeCards, rail,
    spotDots, spotLines: homeLines(st.space), openHer: () => app.go(st.space),
    spotNext: () => app.setState({ space: ORDER[(idx + 1) % 3] }), spotPrev: () => app.setState({ space: ORDER[(idx + 2) % 3] }),
    isDonnaSpace: st.space === 'donna', isMpSpace: st.space === 'mp',
    notCallView: !(sc === 'call' || sc === 'transcript'), notSub: !s.sub,
    sheetOn: !!sh, sh: sh || { title: '', rows: [] }, closeSheet: () => app.setState({ sheet: null }),
    hv: Object.assign(shellWords(st, ctx, parts, V), { donnaName: AG.donna.name, pepperName: AG.pepper.name, mpName: AG.mp.name }),
    toast: st.toast || '', toastOn: !!st.toast, toastUndo: !!st.toastUndo, undo: () => (app.demoMode ? app.setState({ toast: null }) : app.undoToast())
  });
}
