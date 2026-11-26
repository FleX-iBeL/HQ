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
  loadAll() {
    for (const a of Object.values(AREAS)) {
      if (this.isReal(a) && a.load) Promise.resolve().then(() => a.load(this)).catch((err) => console.error('HQ: loading ' + a.NAME, err));
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
    this.loadAll();
    if (typeof document !== 'undefined') {
      document.addEventListener('visibilitychange', () => { if (!document.hidden) this.loadAll(); });
      // Outside demo mode the offline state is the real one; the review switch is demo only.
      api.onOffline((off) => { if (!this.demoMode) { this.setState({ offline: off }); if (!off) this.loadAll(); } });
      if (!this.demoMode && api.offline) this.setState({ offline: true });
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
        mergeInto(parts.agent[k], r.agent[k]);
      }
      Object.assign(parts.sheets, r.sheets || {});
      Object.assign(parts.titles, r.titles || {});
      Object.assign(parts.submit, r.submit || {});
    }
    return Object.assign(out, core.vals(st, ctx, parts));
  }
}
Object.assign(Component.prototype, core.methods, call.methods);
