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
function boxes(st, app, submit) {
  const typed = {}, enter = {};
  for (const name of Object.keys(submit)) {
    typed[name] = (e) => app.setState((x) => ({ drafts: Object.assign({}, x.drafts, { [name]: e.target.value }) }));
    enter[name] = (e) => {
      if (e.key !== 'Enter' || e.isComposing) return;
      const text = (e.target.value || '').trim();
      if (!text) return;
      e.preventDefault();
      app.setState((x) => ({ drafts: Object.assign({}, x.drafts, { [name]: '' }) }));
      submit[name](text);
    };
  }
  return { drafts: st.drafts, typed, enter };
}

// Installed on the app.
export const methods = {
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
  say(t) {
    this.setState({ toast: t, toastUndo: /^(Ticked|Moved|Let go|Note cleared|Deleted|“)|is back on/.test(t) });
    clearTimeout(this._t);
    this._t = setTimeout(() => this.setState({ toast: null }), 4000);
  }
};

// What every area gets: the app, the agents with their cards, the screen and its flags.
export function context(st, app, cards) {
  const AG = {};
  for (const k of ORDER) AG[k] = Object.assign({}, AGENTS[k], cards[k] || {});
  const sc = st.screen;
  const s = { home: sc === 'home', inner: sc !== 'home', herView: sc === 'home' || SPACES.indexOf(sc) >= 0, space: SPACES.indexOf(sc) >= 0,
    donna: sc === 'donna', pepper: sc === 'pepper', mp: sc === 'mp', call: sc === 'call', transcript: sc === 'transcript', chat: sc === 'chat', sub: SUBS.indexOf(sc) >= 0 };
  SUBS.forEach((k) => { s[k] = sc === k; });
  const sa = Object.assign({}, AG[st.space]);
  sa.hasAction = st.space !== 'donna';
  sa.action = st.space === 'pepper' ? () => app.go('checkin') : () => app.go('handover');
  sa.actionLabel = st.space === 'pepper' ? 'Start the check-in' : 'Read the hand-over';
  return { app, AG, sc, s, sa, device: app.device };
}

// The core's render values, given the areas' parts: per agent its home lines and space rows,
// the sheets each area opens, the titles each area gives its screens, and what each of
// its text boxes does with the text on Enter (submit).
export function vals(st, ctx, parts) {
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
    owner: (sc === 'layer' || sc === 'games') ? { label: 'Pepper', accent: '#c2410c' } : (['features', 'sound', 'voices'].indexOf(sc) >= 0 ? { label: 'Settings', accent: '#475569' } : ownerOut),
    title: titles[sc] || '',
    spaceRows, home: () => app.setState({ screen: 'home', stack: [] }), homeCards, rail,
    spotDots, spotLines: homeLines(st.space), openHer: () => app.go(st.space),
    spotNext: () => app.setState({ space: ORDER[(idx + 1) % 3] }), spotPrev: () => app.setState({ space: ORDER[(idx + 2) % 3] }),
    isDonnaSpace: st.space === 'donna', isMpSpace: st.space === 'mp',
    notCallView: !(sc === 'call' || sc === 'transcript'), notSub: !s.sub,
    sheetOn: !!sh, sh: sh || { title: '', rows: [] }, closeSheet: () => app.setState({ sheet: null }),
    toast: st.toast || '', toastOn: !!st.toast, toastUndo: !!st.toastUndo, undo: () => app.setState({ toast: null })
  });
}
