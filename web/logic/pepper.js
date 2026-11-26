// Pepper's area: the map and its layers, check-ins, the six-week games, and her card, home
// lines and space rows.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
//
// The real data is { coaching, games, calls, errs } from /api/coaching, /api/games and
// /api/calls. The screens read everything under the one hole `pp`. In demo mode the same
// shaping runs on SAMPLE below (made up), changed in place in state; the top-level values the
// prototypes have (layers, grid, checklist, ...) stay as they were, for the equivalence check.
import * as demo from './demo/pepper.js';

export const NAME = 'pepper';
export const WIRED = true;
export const LOADING_OK = true;
export { demo };

export const start = { walk: true, pages: demo.pages, feel: null, kept: false, gameId: demo.currentGame, layerN: null, ppFeel: {}, ppUndo: false, ppSaid: '', ppSample: null, ppBusy: false };

// ---- loading ------------------------------------------------------------------------------

const WHAT = { coaching: 'api/coaching', games: 'api/games', calls: 'api/calls' };

async function fetchSome(app, which) {
  const got = await Promise.allSettled(which.map((k) => app.api.get(WHAT[k])));
  app.setData(NAME, (old) => {
    const out = Object.assign({ coaching: null, games: null, calls: null, errs: {} }, old || {});
    out.errs = Object.assign({}, out.errs);
    which.forEach((k, i) => {
      if (got[i].status === 'fulfilled') { out[k] = got[i].value; delete out.errs[k]; } else out.errs[k] = got[i].reason || true;
    });
    return out;
  });
}
export async function load(app) { await fetchSome(app, ['coaching', 'games', 'calls']); }
export const enter = {
  map: (app) => fetchSome(app, ['coaching']),
  layer: (app) => fetchSome(app, ['coaching']),
  checkin: (app) => fetchSome(app, ['coaching']),
  games: (app) => fetchSome(app, ['games']),
  game: (app) => fetchSome(app, ['games']),
  pepper: (app) => fetchSome(app, ['coaching', 'games', 'calls'])
};

// ---- small helpers ------------------------------------------------------------------------

const ISO = /\b\d{4}-\d{2}-\d{2}\b/g;
const dateOf = (iso) => new Date(iso + 'T12:00:00');
const fmt = (iso) => { try { return dateOf(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }); } catch (e) { return iso; } };
const fmtDay = (iso) => { try { return dateOf(iso).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric', month: 'short' }); } catch (e) { return iso; } };
const addDays = (iso, n) => { const d = dateOf(iso); d.setDate(d.getDate() + n); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };
const dow = (iso) => (dateOf(iso).getDay() + 6) % 7;
const pct = (x) => (x == null ? '' : Math.round(x * 100) + '%');
const cap = (t) => (t ? t.charAt(0).toUpperCase() + t.slice(1) : '');
const low = (t) => (t ? t.charAt(0).toLowerCase() + t.slice(1) : '');
const plainName = (n) => (n || '').replace(/\s*\(.*?\)\s*/g, ' ').trim();
const NUM = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six'];
const label = (t) => t.label || t.id;
const clean = (t) => (t || '').replace(ISO, fmtDay);
const todayIso = () => { const d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); };

const READ_KEY = 'hq-coach-read'; // the same key the old page kept, so what was read stays read
function readAt() { try { return parseFloat(localStorage.getItem(READ_KEY) || '0') || 0; } catch (e) { return 0; } }
const unreadOf = (c) => ((c && c.thread) || []).filter((m) => m.from === 'agent' && m.at > readAt()).length;

const why = (e) => (e && e.status === 0 ? 'Couldn’t reach HQ. Try again.' : ((e && e.message) || 'That didn’t work. Try again.'));

// A text box of this area, kept in core's drafts: Enter or its button hands the text on.
function box(st, app, name, done) {
  const value = (st.drafts || {})[name] || '';
  const set = (v) => app.setState((x) => ({ drafts: Object.assign({}, x.drafts, { [name]: v }) }));
  const go = (text) => { const t = (text || '').trim(); if (!t) return; set(''); done(t); };
  return {
    value, input: (e) => set(e.target.value),
    key: (e) => { if (e.key !== 'Enter' || e.isComposing) return; e.preventDefault(); go(e.target.value); },
    keep: () => go(app.state && app.state.drafts ? app.state.drafts[name] : value)
  };
}

// ---- what the made-up demo shows in the real shape ----------------------------------------

const SAMPLE_TODAY = '2026-11-26';
function sample() {
  const items = (n, a) => Array.from({ length: n }, (_, i) => ({ key: String(i + 1), q: demo.checklist[i % demo.checklist.length][0], mark: i < a ? 'answered' : (i === a ? 'parked' : 'open'), note: i < a ? demo.checklist[i % 2][3] : '' }));
  const lay = (n, name, word, a, t) => ({ n, name, word, status: '', counts: { answered: a, parked: a < t ? 1 : 0, later: 0, open: Math.max(0, t - a - 1) }, total: t, items: items(t, a) });
  const days = {};
  const start = '2026-11-15';
  demo.marks.forEach((m, i) => { const d = addDays(start, i); if (m === 'done' || m === 'x') days[d] = { walk: m, pages: m === 'done' ? 20 : 5 }; });
  days['2026-11-18'] = Object.assign({}, days['2026-11-18'], { note: 'A short walk only.' });
  return {
    coaching: {
      on: true, agent: { id: 'pepper', name: 'Pepper' }, named: '', map: true, kept: true,
      layers: [lay(1, demo.layers[0][0], 'done', 5, 5), lay(2, demo.layers[1][0], 'in progress', 7, 12), lay(3, demo.layers[2][0], 'in progress', 3, 10), lay(4, demo.layers[3][0], 'not started', 0, 8), lay(5, demo.layers[4][0], 'not started', 0, 6), lay(6, demo.layers[5][0], 'not started', 0, 6)],
      checkins: [
        { key: 'week:2026-W48', kind: 'week', title: 'The weekly look back', due: true, line: 'Since Thursday 26 November afternoon', when: 'Thursdays, afternoon', score: ['Mornings: 9 of 12 days done.'] },
        { key: 'game:mornings', kind: 'game', title: 'The debrief of Mornings', due: false, line: 'After the game' },
        { key: 'checkin:2027-01-04', kind: 'checkin', title: 'The bigger check-in', due: false, line: 'Next: Monday 4 January' }
      ],
      due: 1, thread: [{ at: 1, from: 'agent', text: demo.card.line }], waiting: false
    },
    games: { games: [
      { id: 'mornings', name: 'Mornings', for: 'Steady mornings', game: 'Walk every morning and read 20 pages, five days a week.', rules: '5 of 7 days', best: 'Up before 7', lean: 'The walk is short', fears: 'Late evenings', honest: 'Friday with Pepper',
        phase: 'playing', setup: '2026-11-08', start, end: addDays(start, 41), look_end: addDays(start, 48), length: 42, day: 12, today: SAMPLE_TODAY,
        tracks: [{ id: 'walk', kind: 'tick', label: 'Morning walk' }, { id: 'pages', kind: 'count', label: 'Pages read', per_day: 20, graph: true }, { id: 'felt', kind: 'diary', label: 'How was today?', feel: demo.feelings }],
        days, diary: [], sums: { walk: { done: 9, x: 2, played: 12, share: 0.75 }, pages: { total: 190, days_hit: 9 }, felt: { entries: 0 } },
        win: { text: '5 of 7 days', need: 30, have: 9, on_track: true }, looks: [{ n: 1, from: start, to: addDays(start, 6), ended: true, look: '' }], debrief: null },
      { id: 'autumn', name: demo.pastGames[0].name, game: 'A walk a day.', phase: 'past', start: '2026-09-01', end: '2026-10-12', look_end: '2026-10-19', length: 42, today: SAMPLE_TODAY,
        tracks: [{ id: 'walk', kind: 'tick', label: 'A walk' }], days: {}, diary: [], sums: { walk: { done: 38, x: 4, played: 42, share: 0.9 } }, win: { text: '5 of 7 days', need: 30, have: 38, won: true }, looks: [], debrief: 'It worked.' }
    ] },
    calls: { calls: [] }, errs: {}
  };
}

// In demo mode a change is made on the sample in state, the way the server would.
function changeSample(st, app, gid, body) {
  const D = JSON.parse(JSON.stringify(st.ppSample || sample()));
  const g = D.games.games.find((x) => x.id === gid);
  if (!g) return;
  const day = body.day || g.today;
  const row = g.days[day] = Object.assign({}, g.days[day]);
  if ('tick' in body) { if (body.tick === 'clear') delete row[body.track]; else row[body.track] = body.tick; }
  if ('count' in body) row[body.track] = Math.max(0, body.set ? Number(body.count) : (row[body.track] || 0) + Number(body.count));
  if ('note' in body) row.note = body.note;
  if ('diary' in body) g.diary = [{ at: g.today + ' 12:00', track: body.track, text: body.diary, feel: body.feel }].concat(g.diary || []);
  if ('week' in body) g.looks = g.looks.map((x) => (String(x.n) === String(body.week) ? Object.assign({}, x, { look: body.text }) : x));
  if ('debrief' in body) g.debrief = body.debrief;
  app.setState({ ppSample: D });
  app.say('Kept');
}

// ---- the game ---------------------------------------------------------------------------

const PHASE = { coming: 'Coming', setup: 'Setup week', playing: 'Playing', 'looking back': 'Looking back', past: 'Past' };
function where(g) {
  if (g.phase === 'playing') return 'Day ' + g.day + ' of ' + g.length + ' · playing';
  if (g.phase === 'coming' || g.phase === 'setup') return PHASE[g.phase] + ' · starts ' + fmt(g.start);
  if (g.phase === 'looking back') return 'Looking back · until ' + fmt(g.look_end);
  return fmt(g.start) + ' to ' + fmt(g.end);
}
// How the game stands against its win line: the words and their colour.
function standing(g) {
  const w = g.win || {};
  if (g.phase === 'past' && w.won != null) return w.won ? ['Won', '#15803d'] : ['Not won this time', '#475569'];
  if (g.phase === 'playing' && w.on_track != null) {
    if (w.on_track) return ['On track', '#15803d'];
    return w.reachable === false ? ['Out of reach now; still worth playing for what it teaches', '#b42318'] : ['Behind, still within reach', '#a16207'];
  }
  return ['', '#475569'];
}
function trackLine(g, t) {
  const s = (g.sums || {})[t.id] || {};
  if (t.kind === 'tick') return s.played ? s.done + ' of ' + s.played + ' days done (' + pct(s.share) + ')' : 'Not started yet';
  if (t.kind === 'count') return (s.total || 0) + (t.target ? ' of ' + t.target : '') + (t.per_day ? ' · ' + (s.days_hit || 0) + ' days with ' + t.per_day : '');
  if (t.kind === 'diary') { const n = s.entries || 0; return n + (n === 1 ? ' entry' : ' entries'); }
  return '';
}

const CELL = { done: ['#c2410c', '#ffffff', 'none'], x: ['#f1f5f9', '#94a3b8', 'line-through'], none: ['#f8fafc', '#475569', 'none'], future: ['#f8fafc', '#cbd5e1', 'none'], out: ['transparent', '#cbd5e1', 'line-through'] };
const WEEKDAYS = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

function gridOf(g, t, change) {
  const cells = [];
  const first = addDays(g.start, -dow(g.start)), last = addDays(g.end, 6 - dow(g.end));
  for (let day = first, i = 0; day <= last && i < 400; day = addDays(day, 1), i++) {
    const d = day;
    const inGame = d >= g.start && d <= g.end, later = d > g.today, v = ((g.days || {})[d] || {})[t.id];
    const noted = !!((g.days || {})[d] || {}).note;
    const k = !inGame ? 'out' : later ? 'future' : (v === 'done' || v === 'x' ? v : 'none');
    const c = CELL[k];
    const n = String(Number(d.slice(8)));
    cells.push({
      key: d, d: n + (noted ? '•' : ''), bg: c[0], fg: c[1], deco: c[2], ring: d === g.today ? '0 0 0 2px #0f172a inset' : 'none',
      off: !inGame || later, tip: fmtDay(d) + (d === g.today ? ' (today)' : '') + (!inGame ? ': not part of the game' : v ? ': ' + (v === 'done' ? 'done' : 'didn’t') : '') + (noted ? ' · ' + g.days[d].note : ''),
      tap: () => { if (inGame && !later) change({ tick: v === 'done' ? 'x' : v === 'x' ? 'clear' : 'done', track: t.id, day: d }); }
    });
  }
  return { label: label(t), line: trackLine(g, t), head: WEEKDAYS.map((w, i) => ({ k: i, w })), cells, todayLine: g.today >= g.start && g.today <= g.end ? 'Today is ' + fmtDay(g.today) + ', the outlined box.' : '' };
}

// A graph of counts as bars: one track a day at a time, several adding up.
function graphOf(g, tracks, title) {
  const n = g.length || 1;
  const days = Array.from({ length: n }, (_, i) => addDays(g.start, i)).filter((d) => d <= g.today);
  const one = tracks.length === 1;
  return tracks.map((t, k) => {
    let run = 0;
    const vals = days.map((d) => { const v = +(((g.days || {})[d] || {})[t.id] || 0); run += v; return one ? v : run; });
    const ref = one ? (t.per_day || 0) : (t.target || 0);
    const top = Math.max(1, ref, ...vals);
    return {
      key: t.id + k, title: (title || label(t)) + (one ? '' : ' · ' + label(t) + ', adding up'),
      bars: Array.from({ length: n }, (_, i) => ({ k: i, h: i < vals.length ? Math.round(100 * vals[i] / top) : 0 })),
      hasLine: ref > 0, lineAt: Math.round(100 * ref / top),
      words: one ? 'A day at a time' + (t.per_day ? ', the dashed line ' + t.per_day + ' a day' : '') : 'The dashed line is ' + (t.target || 'no') + ' target'
    };
  });
}

function shapeGame(st, app, g, all, isDemo) {
  const change = (body) => {
    if (isDemo) return changeSample(st, app, g.id, body);
    return postGames(app, Object.assign({ game: g.id }, body), (old) => patchGame(old, g.id, body));
  };
  const today = (g.days || {})[g.today] || {};
  const playing = g.phase === 'playing';
  const [stand, standC] = standing(g);
  const w = g.win || {};
  const full = w.need != null ? g.length : w.total;
  const winWords = w.text ? 'Win line: ' + w.text + (full ? ' · ' + (w.need != null ? (w.have || 0) + ' of the ' + w.need + ' days it takes' : (w.have || 0) + ' of ' + w.total) : '') : '';
  const tracks = g.tracks || [];
  const todayRows = playing ? tracks.filter((t) => t.kind === 'tick' || t.kind === 'count').map((t) => {
    const v = today[t.id];
    if (t.kind === 'tick') {
      const on = (x) => ({ bg: v === x ? (x === 'done' ? '#c2410c' : '#0f172a') : '#f1f5f9', fg: v === x ? '#ffffff' : '#0f172a' });
      return { key: t.id, name: label(t), isTick: true, isCount: false, done: on('done'), didnt: on('x'),
        tapDone: () => change({ tick: v === 'done' ? 'clear' : 'done', track: t.id }), tapDidnt: () => change({ tick: v === 'x' ? 'clear' : 'x', track: t.id }) };
    }
    const n = v || 0;
    return { key: t.id, name: label(t) + (t.per_day ? ' (' + t.per_day + ' a day)' : ''), isTick: false, isCount: true, n,
      less: () => { if (n > 0) change({ count: -1, track: t.id }); }, more: () => change({ count: 1, track: t.id }) };
  }) : [];
  const noteBox = box(st, app, 'pepperNote', (text) => change({ note: text }));
  const grids = tracks.filter((t) => t.kind === 'tick').map((t) => gridOf(g, t, change));
  let graphs = [];
  tracks.filter((t) => t.kind === 'count' && t.graph).forEach((t) => { graphs = graphs.concat(graphOf(g, [t])); });
  (g.graphs || []).forEach((gr) => {
    const ts = (gr.tracks || []).map((id) => tracks.find((t) => t.id === id)).filter(Boolean);
    if (ts.length) graphs = graphs.concat(graphOf(g, ts, gr.label || ts.map(label).join(' and ')));
  });
  const counts = tracks.filter((t) => t.kind === 'count').map((t) => ({ key: t.id, name: label(t), line: trackLine(g, t) }));
  const diaries = tracks.filter((t) => t.kind === 'diary').map((t) => {
    const picked = (st.ppFeel || {})[t.id] || '';
    const b = box(st, app, 'pepperDiary' + t.id, (text) => { change({ diary: text, feel: picked, track: t.id }); app.setState((x) => ({ ppFeel: Object.assign({}, x.ppFeel, { [t.id]: '' }) })); });
    return {
      key: t.id, name: cap(label(t)), line: trackLine(g, t), canAdd: playing, box: b,
      feels: (t.feel || []).map((f) => {
        const on = picked === f;
        return { name: f, pick: () => app.setState((x) => ({ ppFeel: Object.assign({}, x.ppFeel, { [t.id]: on ? '' : f }) })), bg: on ? '#c2410c' : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
      }),
      entries: (g.diary || []).filter((e) => e.track === t.id).slice(0, 60).map((e, i) => ({ key: e.at + i, when: e.at + (e.feel ? ' · ' + e.feel : ''), text: e.text })),
      none: !(g.diary || []).some((e) => e.track === t.id)
    };
  });
  const cardRows = [['for', 'What it’s for'], ['rules', 'The rules'], ['best', 'At my best'], ['lean', 'What comes easily'], ['fears', 'What could get in the way'], ['honest', 'What keeps me honest']]
    .filter(([k]) => g[k]).map(([k, l]) => ({ key: k, label: l, text: g[k] }));
  const notes = Object.keys(g.days || {}).filter((d) => g.days[d].note).sort().reverse().map((d) => ({ key: d, when: fmtDay(d), text: g.days[d].note }));
  const weeks = (g.looks || []).filter((x) => x.ended || x.look).map((x) => {
    const b = box(st, app, 'pepperWeek' + x.n, (text) => change({ week: String(x.n), text }));
    return { key: 'w' + x.n, title: 'Week ' + x.n + ' · ' + fmt(x.from) + ' to ' + fmt(x.to), look: x.look || '', hasLook: !!x.look, canWrite: !x.look && g.phase !== 'past', notLooked: !x.look && g.phase === 'past', box: b };
  });
  const showDebrief = g.phase === 'looking back' || g.phase === 'past' || !!g.debrief;
  const debriefBox = box(st, app, 'pepperDebrief', (text) => change({ debrief: text }));
  return {
    id: g.id, name: g.name, where: where(g), sentence: g.game || '',
    fill: full ? Math.min(100, Math.round(100 * (w.have || 0) / full)) : 0, hasBar: !!full, hasNeed: w.need != null && !!full, need: full ? Math.min(100, Math.round(100 * (w.need || 0) / full)) : 0,
    stand, standC, hasStand: !!stand, winWords, hasWin: !!winWords,
    setupLine: g.phase === 'setup' || g.phase === 'coming' ? 'Setup week from ' + fmt(g.setup) + ', six weeks from ' + fmt(g.start) + ', look back until ' + fmt(g.look_end) + '. Nothing to tick yet.' : '',
    playing, todayRows, hasToday: playing, todayTitle: 'Today · ' + fmtDay(g.today), noteBox, noted: today.note || '', hasNoted: !!today.note,
    grids, graphs, hasGraphs: graphs.length > 0, counts, diaries, hasDiary: diaries.length > 0,
    cardRows, hasCard: cardRows.length > 0, notes, hasNotes: notes.length > 0,
    weeks, hasWeeks: weeks.length > 0, showDebrief, debrief: g.debrief || '', hasDebrief: !!g.debrief, writeDebrief: showDebrief && !g.debrief, debriefBox,
    undoOn: !isDemo && !!st.ppUndo, said: st.ppSaid ? clean(st.ppSaid) : '', undo: () => postGames(app, { undo: true }), busy: !!st.ppBusy
  };
}

// The new state at once, before the server's answer (which then replaces it).
function patchGame(old, gid, body) {
  if (!old || !old.games || !old.games.games) return old;
  const games = old.games.games.map((g) => {
    if (g.id !== gid) return g;
    const day = body.day || g.today;
    const days = Object.assign({}, g.days), row = Object.assign({}, days[day]);
    if ('tick' in body) { if (body.tick === 'clear') delete row[body.track]; else row[body.track] = body.tick; }
    else if ('count' in body) row[body.track] = Math.max(0, (row[body.track] || 0) + Number(body.count));
    else return g;
    days[day] = row;
    return Object.assign({}, g, { days });
  });
  return Object.assign({}, old, { games: Object.assign({}, old.games, { games }) });
}

async function postGames(app, body, patch) {
  if (patch) app.setData(NAME, patch);
  app.setState({ ppBusy: true });
  try {
    const d = await app.api.post('api/games', body, 'games');
    app.setData(NAME, (old) => Object.assign({}, old, { games: d }));
    app.setState({ ppUndo: false, ppSaid: d.said || '', ppBusy: false });
    // its Undo is the toast's: the last change, as the server keeps it
    if (d.said) app.say(clean(d.said), d.undo && !body.undo ? () => postGames(app, { undo: true }) : null);
  } catch (e) {
    app.setState({ ppBusy: false });
    app.say(why(e));
    fetchSome(app, ['games']);
  }
}

async function postCoaching(app, body) {
  try {
    const d = await app.api.post('api/coaching', body, 'coaching');
    app.setData(NAME, (old) => Object.assign({}, old, { coaching: d }));
    if (d.said) app.say(clean(d.said));
  } catch (e) {
    app.say(why(e));
    fetchSome(app, ['coaching']);
  }
}

// ---- the whole area ---------------------------------------------------------------------

function offLine(c, what) {
  if (!c) return '';
  if (c.off === 'Free') return 'Free is on: none of your files. Turn it off in Settings to see your ' + what + '.';
  if (!c.on) return 'Life coaching is off. Turn it on in Settings, under What HQ helps you with.';
  return '';
}

function shapeReal(st, ctx, D, isDemo) {
  const { app } = ctx;
  const C = D && D.coaching, G = D && D.games, errs = (D && D.errs) || {};
  const who = (C && C.agent && C.agent.name) || 'Pepper';
  const retry = () => (isDemo ? null : fetchSome(app, ['coaching', 'games', 'calls']));

  // Start a call with Pepper about one layer or one check-in, as the old Coaching place does.
  const startAbout = (ref) => {
    if (isDemo) return app.startCall('pepper');
    if (st.onCall) return app.say('You’re on a call: just say what you’d like to work on.');
    if (st.free) return app.say('Free is on: turn it off in Settings to work on this with ' + who + '.');
    app.startCall((C && C.agent && C.agent.id) || 'pepper', { about_coaching: ref });
  };

  // The map and its layers
  const cOff = offLine(C, 'coaching');
  const m = { note: '', retryOn: false, startOn: false, start: () => startAbout('layer:1'), layers: [], hasLayers: false };
  if (!C) { m.note = errs.coaching ? 'Couldn’t load the map. ' + why(errs.coaching) : 'Loading…'; m.retryOn = !!errs.coaching; }
  else if (cOff) m.note = cOff;
  else if (!C.map) { m.note = 'Your map isn’t started yet. Go through it with ' + who + ', one layer per session, and it shows up here.'; m.startOn = true; }
  else {
    m.layers = (C.layers || []).map((L) => {
      const c = L.counts || {}, tot = L.total || 1, put = (c.parked || 0) + (c.later || 0);
      return { key: 'L' + L.n, name: plainName(L.name), st: cap(L.word) + ' · ' + (c.answered || 0) + ' of ' + L.total, pct: Math.round(100 * (c.answered || 0) / tot), put: Math.round(100 * put / tot), open: () => app.go('layer', { layerN: L.n }) };
    });
    m.hasLayers = m.layers.length > 0;
  }

  // One layer
  const MARK = { answered: ['Answered', '#15803d'], parked: ['Parked', '#a16207'], later: ['Later', '#475569'], open: ['Open', '#64748b'] };
  const L = C && C.on && (C.layers || []).find((x) => x.n === st.layerN);
  const l = { on: false, note: m.note || (C && !L ? 'This layer isn’t on the map.' : ''), retryOn: m.retryOn };
  if (L) {
    const c = L.counts || {}, tot = L.total || 1, put = (c.parked || 0) + (c.later || 0);
    Object.assign(l, {
      on: true, title: L.n + '. ' + plainName(L.name), word: cap(L.word), headline: (c.answered || 0) + ' of ' + L.total + ' answered',
      pct: Math.round(100 * (c.answered || 0) / tot), put: Math.round(100 * put / tot),
      items: (L.items || []).map((it) => ({ key: it.key, q: it.q, mark: (MARK[it.mark] || MARK.open)[0], mc: (MARK[it.mark] || MARK.open)[1], note: it.note || '', hasNote: !!it.note })),
      empty: !(L.items || []).length,
      startLabel: L.word === 'done' ? 'Go back over it with ' + who : (c.answered ? 'Continue with ' + who : 'Start with ' + who),
      start: () => startAbout('layer:' + L.n)
    });
  }

  // Check-ins
  const ck = { note: m.note && !m.startOn ? m.note : '', retryOn: m.retryOn, due: [], rest: [], noneDue: false, hasRest: false, keptLine: '' };
  if (C && C.on && !cOff) {
    const SUB = { week: who + ' looks back at the week with you and sets up the next one.', game: who + ' looks back at the game with you: was it fun, was it useful, what did you learn.', checkin: who + ' looks at how it’s going with you, and what comes next.' };
    const cs = C.checkins || [];
    ck.due = cs.filter((c) => c.due).map((c) => ({
      key: c.key, kicker: 'Due · ' + low(c.line || ''), title: c.title, sub: SUB[c.kind] || '', score: (c.score || []).map((t, i) => ({ k: i, t })), hasScore: !!(c.score || []).length,
      start: () => startAbout(c.key), later: () => (isDemo ? app.say('Not now') : postCoaching(app, { later: c.key }))
    }));
    ck.rest = cs.filter((c) => !c.due).map((c) => ({ key: c.key, title: c.title, when: c.done ? 'Done ' + fmtDay(String(c.done).slice(0, 10)) : (c.line || '').replace(/^Next: /, '') }));
    if (C.map && !cs.some((c) => c.kind === 'week')) ck.rest.unshift({ key: 'noweek', title: 'The weekly look back', when: 'Not set yet' });
    ck.noneDue = !ck.due.length;
    ck.hasRest = ck.rest.length > 0;
    if (C.map && !C.kept) ck.keptLine = 'HQ starts keeping your check-ins in a moment.';
    if (!C.map) ck.note = 'Your map isn’t started yet. The check-ins come with it.';
  }
  ck.hasKept = !!ck.keptLine;

  // The games
  const gOff = offLine(C, 'games') || (G && G.off === 'Free' ? offLine(G, 'games') : '');
  const list = (G && G.games) || [];
  const gs = { note: '', retryOn: false, live: [], past: [], hasPast: false };
  if (!G) { gs.note = errs.games ? 'Couldn’t load the games. ' + why(errs.games) : 'Loading…'; gs.retryOn = !!errs.games; }
  else if (gOff) gs.note = gOff;
  else if (G.error) gs.note = G.error;
  else if (!list.length) gs.note = 'No six-week game yet. Design one with ' + who + ' on a call, and it shows up here.';
  else {
    const row = (g) => { const [s, c] = standing(g); return { key: g.id, kicker: g.phase === 'playing' ? 'Playing · day ' + g.day + ' of ' + g.length : where(g), name: g.name, sentence: g.game || '', stand: s, standC: c, open: () => app.go('game', { gameId: g.id }) }; };
    gs.live = list.filter((g) => g.phase !== 'past').map(row);
    gs.past = list.filter((g) => g.phase === 'past').map((g) => { const [s] = standing(g); return { key: g.id, name: g.name, meta: fmt(g.start) + ' to ' + fmt(g.end) + (s ? ' · ' + low(s) : ''), open: () => app.go('game', { gameId: g.id }) }; });
    gs.hasPast = gs.past.length > 0;
  }
  // The game that's open: its own id, else the one being played
  const live = list.filter((g) => g.phase !== 'past');
  const og = list.find((g) => g.id === st.gameId) || live[0] || list[0];
  const gm = og && !gOff ? shapeGame(st, app, og, list, isDemo) : null;
  const game = { on: !!gm, note: gm ? '' : (gs.note || 'No six-week game yet.'), retryOn: gs.retryOn, g: gm || {} };

  // Her card, home lines and space rows
  const dueC = C && C.on ? (C.checkins || []).filter((c) => c.due) : [];
  const playingG = list.find((g) => g.phase === 'playing') || live[0];
  const openLayer = C && C.on && C.map ? (C.layers || []).find((x) => x.word !== 'done') : null;
  const layerShort = (x) => plainName(x.name) + ', ' + ((x.counts || {}).answered || 0) + ' of ' + x.total + ' answered';
  const SHORT = { 'On track': 'on track', 'Behind, still within reach': 'behind', 'Out of reach now; still worth playing for what it teaches': 'out of reach' };
  const gameShort = (g) => (g.phase === 'playing' ? 'Day ' + g.day + (SHORT[standing(g)[0]] ? ', ' + SHORT[standing(g)[0]] : '') : where(g));
  const unread = unreadOf(C);
  const lastHer = ((C && C.thread) || []).filter((x) => x.from === 'agent').slice(-1)[0];
  // Her last line on the coaching line, cut at a sentence or a word
  const herLine = (() => {
    const t = (lastHer && lastHer.text) || '';
    if (t.length <= 160) return t;
    const s = t.slice(0, 160), dot = s.lastIndexOf('. ');
    return dot > 40 ? s.slice(0, dot + 1) : s.slice(0, s.lastIndexOf(' ')) + '…';
  })();
  let card;
  if (!C) card = { kicker: '', headline: errs.coaching ? 'Couldn’t load' : 'Loading…', sub: '', line: '' };
  else if (cOff) card = { kicker: 'Life coaching', headline: 'Off', sub: 'Turn it on in Settings', line: '' };
  else if (dueC.length) card = { kicker: 'Due · ' + low(dueC[0].line || ''), headline: dueC[0].title, sub: 'Whenever you’re ready', line: herLine };
  else if (playingG) card = { kicker: 'The six-week game', headline: playingG.name, sub: gameShort(playingG), line: herLine };
  else if (openLayer) card = { kicker: 'The map', headline: plainName(openLayer.name), sub: ((openLayer.counts || {}).answered || 0) + ' of ' + openLayer.total + ' answered', line: '' };
  else card = { kicker: 'Life coaching', headline: C.map ? 'The map is done' : 'Start your map', sub: '', line: '' };
  // the Start-the-check-in button under her card shows only while a check-in is due
  card.actionOn = dueC.length > 0;
  const homeLines = [];
  if (C && !cOff) {
    if (dueC.length > 1) homeLines.push({ t: NUM[Math.min(dueC.length, 6)] + ' check-ins due', c: '#b42318', w: '600' });
    if (playingG && card.kicker !== 'The six-week game') homeLines.push({ t: 'The game: ' + (playingG.phase === 'playing' ? 'day ' + playingG.day + ' of ' + playingG.length + (SHORT[standing(playingG)[0]] ? ', ' + SHORT[standing(playingG)[0]] : '') : low(where(playingG))), c: '#0f172a', w: '400' });
    if (openLayer && card.kicker !== 'The map') homeLines.push({ t: 'The map: ' + low(layerShort(openLayer)), c: '#0f172a', w: '400' });
    if (unread) homeLines.push({ t: unread + ' new on the coaching line', c: '#c2410c', w: '600' });
  }
  const calls = ((D && D.calls && D.calls.calls) || []).filter((x) => (x.agent || '').toLowerCase() === who.toLowerCase());
  const lastCall = (() => {
    const c = calls[0];
    if (!c || !c.date) return 'None yet';
    const t = todayIso();
    if (c.date === t) return 'Today';
    if (c.date === addDays(t, -1)) return 'Yesterday';
    if (c.date > addDays(t, -7)) return dateOf(c.date).toLocaleDateString(undefined, { weekday: 'long' });
    return fmt(c.date);
  })();
  const off = !!cOff;
  const rows = [
    ['The map', !C ? '' : off ? 'Off' : !C.map ? 'Not started' : openLayer ? plainName(openLayer.name) + ' ' + ((openLayer.counts || {}).answered || 0) + ' of ' + openLayer.total : 'Done', 'map'],
    ['The six-week game', !G ? '' : off ? 'Off' : playingG ? gameShort(playingG) : list.length ? 'None playing' : 'None yet', 'games'],
    ['Check-ins', !C ? '' : off ? 'Off' : dueC.length ? NUM[Math.min(dueC.length, 6)] + ' due' : 'None due', 'checkin', dueC.length ? '#b42318' : null, dueC.length ? '600' : null],
    ['Coaching line', unread ? unread + ' new' : '', ['chat', { chatAgent: 'pepper' }], unread ? '#c2410c' : null, unread ? '600' : null],
    ['Her notes', '', 'notes'],
    ['Past calls', D && D.calls ? lastCall : '', 'pastCalls']
  ];

  return { pp: { m, l, ck, gs, game, retry }, card, rows, homeLines, layerTitle: l.title || 'A layer' };
}

// ---- vals ---------------------------------------------------------------------------------

export const card = (st, D) => (D === demo ? D.card : shapeCardOnly(st, D));
function shapeCardOnly(st, D) { return shapeReal(st, { app: null }, D, false).card; }

const GRID = { done: ['#c2410c', '#ffffff', 'none'], x: ['#f1f5f9', '#94a3b8', 'none'], none: ['#f8fafc', '#cbd5e1', 'none'], today: ['#ffffff', '#0f172a', '0 0 0 2px #0f172a inset'], future: ['#f8fafc', '#cbd5e1', 'none'] };

export function vals(st, ctx, D) {
  const { app } = ctx;
  const isDemo = D === demo;
  const R = shapeReal(st, ctx, isDemo ? (st.ppSample || sample()) : D, isDemo);
  if (!isDemo) {
    return { agent: { pepper: { homeLines: R.homeLines, rows: R.rows } }, sheets: {}, titles: { layer: R.layerTitle }, values: { pp: R.pp } };
  }
  // Demo mode: the prototypes' own values (the equivalence check reads these), plus pp.
  const layers = D.layers.map((l) => ({ name: l[0], st: l[1], pct: l[2], open: () => app.go('layer') }));
  const grid = D.marks.map((m, i) => {
    if (m === 'today') m = st.walk ? 'done' : 'today';
    const v = GRID[m] || GRID.none;
    return { d: D.days[i], bg: v[0], fg: v[1], ring: i === D.todayIndex ? '0 0 0 2px #0f172a inset' : v[2] };
  });
  const checklist = D.checklist.map((c) => ({ q: c[0], mark: c[1], mc: c[2], note: c[3], hasNote: !!c[3] }));
  const feelChips = D.feelings.map((f) => {
    const on = st.feel === f;
    return { name: f, pick: () => app.setState({ feel: f }), bg: on ? '#c2410c' : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });
  return {
    agent: { pepper: { homeLines: D.homeLines, rows: D.rows } },
    sheets: {},
    titles: { layer: D.layerTitle },
    values: {
      pp: R.pp,
      layers, grid, checklist, feelChips,
      pastGames: D.pastGames.map((g) => Object.assign({}, g, { open: () => app.go('game', { gameId: g.id }) })),
      walkToggle: () => app.setState((x) => ({ walk: !x.walk })), walkLabel: st.walk ? 'Done' : 'Not yet', walkBg: st.walk ? '#c2410c' : '#f1f5f9', walkFg: st.walk ? '#ffffff' : '#0f172a',
      pages: st.pages, pagesUp: () => app.setState((x) => ({ pages: x.pages + 1 })), pagesDown: () => app.setState((x) => ({ pages: Math.max(0, x.pages - 1) })),
      openGame: () => app.go('game', { gameId: D.currentGame }),
      kept: st.kept, notKept: !st.kept, keepIt: () => { app.setState({ kept: true }); app.say('Kept. Pepper reads it at the check-in'); }
    }
  };
}
