// The app's one component: it merges the areas. The conventions an area follows (start,
// vals, WIRED, demo, load, enter, card, methods) are at the top of logic/core.js and in
// WIRING.md. This file only gathers them; nobody wiring an area needs to edit it.
import { DCLogic } from './engine.js';
import { api } from './api.js';
import * as core from './logic/core.js';
import * as call from './logic/call.js';
import * as texts from './logic/texts.js';
import * as agenda from './logic/agenda.js';
import * as todo from './logic/todo.js';
import * as lists from './logic/lists.js';
import * as inbox from './logic/inbox.js';
import * as pepper from './logic/pepper.js';
import * as mp from './logic/mp.js';
import * as settings from './logic/settings.js';

export const AREAS = { call, texts, agenda, todo, lists, inbox, pepper, mp, settings };
// Whose card text each agent shows (kicker, headline, sub, line).
const CARDS = { donna: agenda, pepper, mp };

const plain = (v) => v && typeof v === 'object' && !Array.isArray(v);
// An agent's space rows from several areas: a list as one area gives it, and the keyed rows of
// the others ({ texts: [...], pastCalls: [...] }). A keyed row takes the place of the list's row
// with the same label (so texts and past calls fill Pepper's and Moneypenny's rows too), else it
// comes after the list.
function joinRows(a, b) {
  if (!a) return b;
  if (!b) return a;
  if (plain(a) && plain(b)) return Object.assign({}, a, b);
  const list = (Array.isArray(a) ? a : b).slice(), keyed = Array.isArray(a) ? b : a;
  for (const row of Object.values(keyed)) {
    if (!Array.isArray(row)) continue;
    const i = list.findIndex((r) => Array.isArray(r) && r[0] === row[0]);
    if (i >= 0) { if (row[1] !== '' || list[i][1] === '') list[i] = row; } else list.push(row);
  }
  return list;
}
// Values two areas both give as plain objects (like `chat`) are merged one level deep.
function mergeInto(out, add) {
  for (const k in add) out[k] = plain(out[k]) && plain(add[k]) ? Object.assign({}, out[k], add[k]) : add[k];
  return out;
}

export function startState(design) {
  const st = Object.assign({}, core.start, { data: {} });
  for (const a of Object.values(AREAS)) Object.assign(st, JSON.parse(JSON.stringify(a.start)));
  if (design) st.design = design;
  return st;
}

export class Component extends DCLogic {
  constructor(props) {
    super(props);
    this.state = startState(this.props.design);
    this.device = this.props.device || 'phone';
    this.demoMode = !!this.props.demo;
    this.api = api;
  }
  // Real data only for an area that is wired, and never in demo mode.
  isReal(a) { return !!a.WIRED && !this.demoMode; }
  // The data an area renders from: its demo module, or state.data[area] (null while loading).
  source(a) { return this.isReal(a) ? (this.state.data[a.NAME] ?? null) : a.demo; }
  // An area keeps its data with app.setData('todo', {...}); it lands in state.data.todo.
  setData(name, patch) {
    this.setState((x) => ({ data: Object.assign({}, x.data, { [name]: typeof patch === 'function' ? patch(x.data[name]) : patch }) }));
  }
  // load(app) for every wired area: at mount, and when the app comes back (visible, online).
  // One load per area at a time: a load asked while that area's load still runs is dropped, and
  // a return to the foreground loads again only when the last load is over a minute old (force:
  // at mount and when the server answers again after being away).
  loadAll(force) {
    const now = Date.now();
    this._loading = this._loading || {};
    this._loadedAt = this._loadedAt || {};
    for (const a of Object.values(AREAS)) {
      if (!this.isReal(a) || !a.load) continue;
      if (this._loading[a.NAME]) continue;
      if (!force && now - (this._loadedAt[a.NAME] || 0) < 60000) continue;
      this._loading[a.NAME] = true;
      this._loadedAt[a.NAME] = now;
      Promise.resolve().then(() => a.load(this)).catch((err) => console.error('HQ: loading ' + a.NAME, err))
        .then(() => { this._loading[a.NAME] = false; });
    }
  }
  // enter[screen](app) for every wired area, when that screen is opened (core's go()).
  entered(screen) {
    for (const a of Object.values(AREAS)) {
      const fn = this.isReal(a) && a.enter && a.enter[screen];
      if (fn) Promise.resolve().then(() => fn(this)).catch((err) => console.error('HQ: opening ' + screen + ' in ' + a.NAME, err));
    }
  }
  componentDidMount() {
    if (this._mountedOnce) return; // a design or device switch mounts again with the same state
    this._mountedOnce = true;
    this.loadAll(true);
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => { if (!document.hidden) { this.setState({ clockNow: Date.now() }); this.loadAll(false); } });
      // Outside demo mode the offline state is the real one; the review switch is demo only.
      api.onOffline((off) => { if (!this.demoMode) { this.setState({ offline: off }); if (!off) this.loadAll(true); } });
      if (!this.demoMode && api.offline) this.setState({ offline: true });
      // The clock: one tick a minute, on the minute, for whatever shows the time (Now, the date,
      // "now 14:20"); none while the page is hidden.
      if (!this.demoMode) {
        const tick = () => {
          if (!document.hidden) this.setState({ clockNow: Date.now() });
          this._clock = setTimeout(tick, 60000 - (Date.now() % 60000) + 50);
        };
        this._clock = setTimeout(tick, 60000 - (Date.now() % 60000) + 50);
      }
    }
  }
  // Switch the design; boot.js mounts the new design's templates with this same state.
  useDesign(id) {
    this.setState({ design: id });
    if (this.props.onDesign) this.props.onDesign(id);
  }
  renderVals() {
    const st = this.state;
    const cards = {};
    for (const k in CARDS) { const D = this.source(CARDS[k]); cards[k] = D ? CARDS[k].card(st, D) : {}; }
    const ctx = core.context(st, this, cards);
    const parts = { agent: {}, sheets: {}, titles: {}, submit: {} };
    const out = {};
    for (const a of Object.values(AREAS)) {
      const D = this.source(a);
      if (D == null && !a.LOADING_OK) continue; // still loading: its holes stay empty
      const r = a.vals(st, ctx, D);
      mergeInto(out, r.values || {});
      for (const k in r.agent || {}) {
        parts.agent[k] = parts.agent[k] || {};
        const rows = r.agent[k].rows;
        const rest = Object.assign({}, r.agent[k]); delete rest.rows;
        mergeInto(parts.agent[k], rest);
        // in demo mode the prototypes' own rows stand as they are (a list replaces keyed rows)
        if (rows) parts.agent[k].rows = this.demoMode ? (plain(parts.agent[k].rows) && plain(rows) ? Object.assign({}, parts.agent[k].rows, rows) : rows) : joinRows(parts.agent[k].rows, rows);
      }
      Object.assign(parts.sheets, r.sheets || {});
      Object.assign(parts.titles, r.titles || {});
      Object.assign(parts.submit, r.submit || {});
    }
    return Object.assign(out, core.vals(st, ctx, parts, out));
  }
}
Object.assign(Component.prototype, core.methods, call.methods);
