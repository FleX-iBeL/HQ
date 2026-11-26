// The settings area: settings and the design picker, features, voices, sound, weather,
// the tutorial and its tour, and the states to try: first run, Free, offline, texts off,
// an incoming call.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
//
// Real data: /api/features (what HQ helps you with, and the maps key), /api/agents (the
// names, voices and Free-only), /api/weather, /tour.json. What the old page keeps on the
// device stays on the device under the same names: hq-voice-<agent>, hq-free, hq-sound,
// hq-mic, hq-out, hq-theme, hq-wx-gps, hq-tour-seen. Everything the settings templates
// show from real data is under one value, `setv`; the prototypes' own values are still
// given for the demo and its equivalence check.
import * as demo from './demo/settings.js';
// Look: theme.apply keeps the pick as hq-theme (as the old page did) and shows it at once.
import * as theme from '../theme.js';

export const NAME = 'settings';
export const WIRED = true;
// Settings draw before their data is in: the design picker, Free and the states never wait.
export const LOADING_OK = true;
export { demo };
import { DESIGNS } from './core.js';

export const start = {
  rain: true, offline: false, fresh: false, free: false,
  feat: Object.assign({}, demo.featuresOn), voices: Object.assign({}, demo.voicesPicked), place: 'here', tour: -1,
  voiceIds: {}, sound: true, look: 'system', mic: '', out: '', tourPiece: null, tourSeen: [], featBusy: '', keySaid: '', wxBusy: false,
  keepSound: false, tourOpened: true, tourAt: 'bottom', tourFound: true
};

// The first sentence of an agent's character, for the line under her name in Voices.
const firstSentence = (t) => { const m = /^(.+?[.!?])(\s|$)/.exec(String(t).trim()); return (m ? m[1] : String(t).trim()).slice(0, 160); };
const sw = (on) => ({ bg: on ? '#16a34a' : '#cbd5e1', just: on ? 'flex-end' : 'flex-start' });

// The voices an agent can have (config.VOICES), with the old page's names.
const VOICES = [['af_heart', 'Heart'], ['af_bella', 'Bella'], ['am_michael', 'Michael'], ['bf_isabella', 'Isabella (British)'], ['bf_emma', 'Emma (British)'],
  ['am_adam', 'Adam'], ['am_eric', 'Eric'], ['bm_george', 'George (British)'], ['bm_fable', 'Fable (British)']];
const VOICE_NAME = Object.fromEntries(VOICES);
// The core's agent keys and the server's agent ids.
const ID = { donna: 'donna', pepper: 'pepper', mp: 'moneypenny' };

const store = {
  get(k) { try { return typeof localStorage === 'undefined' ? null : localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { if (typeof localStorage === 'undefined') return; if (v == null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
};
const json = (k, d) => { try { return JSON.parse(store.get(k) || 'null') || d; } catch (e) { return d; } };

// Where the page runs (the old page's own test): the phone decides the mic and sound itself.
const UA = typeof navigator !== 'undefined' ? navigator.userAgent || '' : '';
const IS_IOS = /iPhone|iPad|iPod/.test(UA) || (/Macintosh/.test(UA) && typeof navigator !== 'undefined' && navigator.maxTouchPoints > 1);
const IS_MAC = /Macintosh|Mac OS X/.test(UA) && !IS_IOS;
const IS_PHONE = IS_IOS || /Android.*Mobile|Mobile.*Android/.test(UA)
  || (typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches && !matchMedia('(any-pointer: fine)').matches);
const CAN_SINK = typeof HTMLMediaElement !== 'undefined' && 'setSinkId' in HTMLMediaElement.prototype;

function put(app, patch) {
  app.setData(NAME, (o) => {
    const x = Object.assign({ err: {} }, o || {});
    for (const k in patch) if (k !== 'err') x[k] = patch[k];
    x.err = Object.assign({}, x.err, patch.err || {});
    return x;
  });
}
async function read(app, key, path) {
  try { const v = await app.api.get(path); put(app, { [key]: v, err: { [key]: '' } }); return v; }
  catch (e) { put(app, { err: { [key]: e.message || 'failed' } }); return null; }
}

function devPick(k) { return json(k, null); }

// The tutorial's spotlight: an outline round the control a step is about, on the real screen, drawn over the page
// (outside the templates) once the screen has rendered. A spot is a CSS selector, or `text:` and the words the
// control starts with. When it isn't there, the card says so and the screen shows without a spotlight.
let spotEl = null, spotWant = '', spotTimer = 0, spotColour = '#6d28d9';
function findSpot(spot) {
  if (!spot || typeof document === 'undefined') return null;
  const root = document.getElementById('app');
  if (!root) return null;
  let list = [];
  if (spot.startsWith('text:')) {
    const words = spot.slice(5).trim().toLowerCase();
    list = [...root.querySelectorAll('button, a, [role=button], .row, .chip, .pill, .small, h2, .lab, label')].filter((n) => (n.textContent || '').trim().toLowerCase().startsWith(words));
  } else { try { list = [...root.querySelectorAll(spot)]; } catch (e) { list = []; } }
  return list.find((n) => { if (n.closest('[data-tour-card]')) return false; const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0 && n.offsetParent !== null; }) || null;
}
function placeSpotSoon(app, spot, colour) {
  if (typeof document === 'undefined') return;
  spotWant = spot;
  if (colour) spotColour = colour;
  if (!spot && !spotEl) return;
  if (spotTimer) return; // one look per burst of renders; it reads spotWant when it runs
  spotTimer = setTimeout(() => { spotTimer = 0; placeSpot(app); }, 150); // after the render (a timer: a hidden page gets no frames)
}
function placeSpot(app) {
  if (!app) return;
  const want = spotWant, colour = spotColour;
  const el = want ? findSpot(want) : null;
  if (!el) {
    if (spotEl) { spotEl.remove(); spotEl = null; }
    if (want && app.state.tourFound !== false && app.state.tour >= 0) app.setState({ tourFound: false, tourAt: 'bottom' });
    else if (!want && app.state.tour >= 0 && app.state.tourAt !== 'bottom') app.setState({ tourAt: 'bottom' });
    return;
  }
  if (el.scrollIntoView) { const r0 = el.getBoundingClientRect(); if (r0.top < 0 || r0.bottom > window.innerHeight) el.scrollIntoView({ block: 'center' }); }
  const r = el.getBoundingClientRect(), pad = 6;
  if (!spotEl) {
    spotEl = document.createElement('div');
    spotEl.setAttribute('aria-hidden', 'true');
    document.body.appendChild(spotEl);
  }
  const still = typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  Object.assign(spotEl.style, { position: 'fixed', zIndex: '24', pointerEvents: 'none', borderRadius: '16px', left: (r.left - pad) + 'px', top: (r.top - pad) + 'px',
    width: (r.width + 2 * pad) + 'px', height: (r.height + 2 * pad) + 'px', transition: still ? 'none' : 'all .25s ease',
    boxShadow: '0 0 0 3px ' + (colour || '#6d28d9') + ', 0 0 0 9999px rgba(15,23,42,0.45)' });
  // the card on the side with more room, away from the spotlight
  const at = r.top + r.height / 2 > window.innerHeight * 0.55 ? 'top' : 'bottom';
  if (app.state.tourAt !== at || app.state.tourFound === false) app.setState({ tourAt: at, tourFound: true });
}
if (typeof window !== 'undefined') window.addEventListener('resize', () => { if (spotEl) placeSpot(window.HQ && window.HQ.component); });
async function listDevices(app) {
  if (typeof navigator === 'undefined' || !navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) { put(app, { devices: { can: false, ins: [], outs: [] } }); return; }
  let list = [];
  try { list = await navigator.mediaDevices.enumerateDevices(); } catch (e) { list = []; }
  const of = (kind) => list.filter((d) => d.kind === kind && d.deviceId && d.deviceId !== 'default' && d.deviceId !== 'communications').map((d) => ({ id: d.deviceId, label: d.label }));
  put(app, { devices: { can: true, ins: of('audioinput'), outs: of('audiooutput') } });
}

// The weather where you are (when allowed) or at the home place, as the old page asks.
let wxPos = null;
function locate() {
  return new Promise((done) => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) return done(null);
    navigator.geolocation.getCurrentPosition((p) => { wxPos = { lat: p.coords.latitude.toFixed(2), lon: p.coords.longitude.toFixed(2) }; done(wxPos); },
      () => done(null), { enableHighAccuracy: false, timeout: 10000, maximumAge: 600000 });
  });
}
async function loadWeather(app, fresh) {
  const pos = store.get('hq-wx-gps') === '1' ? (wxPos || await locate()) : null;
  const q = [fresh ? 'fresh=1' : '', pos ? 'lat=' + pos.lat + '&lon=' + pos.lon : ''].filter(Boolean).join('&');
  return read(app, 'weather', 'api/weather' + (q ? '?' + q : ''));
}

let wxTimer = 0;
export async function load(app) {
  // What this device keeps, as the old page keeps it.
  const voiceIds = {};
  for (const k of Object.keys(ID)) { const v = store.get('hq-voice-' + ID[k]) || store.get('hq-voice'); if (v && VOICE_NAME[v]) voiceIds[k] = v; }
  const look = store.get('hq-theme');
  app.setState({ voiceIds, free: store.get('hq-free') === 'on', sound: store.get('hq-sound') !== 'off',
    look: look === 'light' || look === 'dark' ? look : 'system', tourSeen: json('hq-tour-seen', []),
    keepSound: store.get('hq-keep-sound') === 'on', tourOpened: store.get('hq-tour-opened') === '1' });
  put(app, {});
  const [, , , wx] = await Promise.all([read(app, 'features', 'api/features'), read(app, 'agents', 'api/agents'), read(app, 'tour', 'tour.json'), loadWeather(app, false)]);
  // The server only keeps the weather once something asked for it fresh: read it fresh once, so the chip on home has degrees.
  if (wx && !wx.now && !wx.off && !wx.error) loadWeather(app, true);
  // The weather is read again every 15 minutes while the page is shown (the server only reads
  // the weather service again when its last read is over 15 minutes old).
  if (!wxTimer && typeof setInterval !== 'undefined') wxTimer = setInterval(() => { if (typeof document === 'undefined' || !document.hidden) loadWeather(app, true); }, 15 * 60000);
}

export const enter = {
  settings: (app) => read(app, 'features', 'api/features'),
  features: (app) => read(app, 'features', 'api/features'),
  sound: (app) => listDevices(app),
  weather: (app) => loadWeather(app, true),
  tutorial: (app) => { store.set('hq-tour-opened', '1'); if (!app.state.tourOpened) app.setState({ tourOpened: true }); return read(app, 'tour', 'tour.json'); }
};

// The tutorial's pieces that still fit the new design (see the report for the others).
const DROP_PIECES = new Set(['news', 'team', 'hours', 'sprint', 'mac']);
const DROP_STEPS = new Set(['notes:Feedback for HQ', 'notes:Connect to the person who makes HQ', 'notes:Invite someone to send you feedback',
  'yours:Change it, add to it', 'yours:Coming soon: shared best practices']);
// Who a piece's Ask button calls when tour.json doesn't say: the agent the piece is about.
const PIECE_AGENT = { coaching: 'pepper', game: 'pepper', moneypenny: 'mp', updates: 'mp', twohq: 'mp', server: 'mp', phone: 'mp', yours: 'mp' };
const AGENT_KEY = { donna: 'donna', pepper: 'pepper', moneypenny: 'mp', mp: 'mp' };

// The weather's pictures, drawn as one stroke path each in the design's icon style.
export const WX_PATH = {
  sun: 'M7 12a5 5 0 1 0 10 0a5 5 0 1 0-10 0M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42',
  moon: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z',
  partly: 'M12 2v2M4.93 4.93l1.41 1.41M20 12h2M19.07 4.93l-1.41 1.41M15.95 12.65A4 4 0 0 0 8.35 9.6M13 22H7a5 5 0 1 1 4.9-6H13a3 3 0 0 1 0 6z',
  cloud: 'M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z',
  fog: 'M4 14.9A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.2M16 17H7M17 21H9',
  drizzle: 'M20 16.2A4.5 4.5 0 0 0 17.5 8h-1.8A7 7 0 1 0 4 14.9M8 19v2M8 13v2M16 19v2M16 13v2M12 21v2M12 15v2',
  rain: 'M20 16.2A4.5 4.5 0 0 0 17.5 8h-1.8A7 7 0 1 0 4 14.9M16 14v6M8 14v6M12 16v6',
  snow: 'M20 17.58A5 5 0 0 0 18 8h-1.26A8 8 0 1 0 4 16.25M8 16h.01M8 20h.01M12 18h.01M12 22h.01M16 16h.01M16 20h.01',
  storm: 'M19 16.9A5 5 0 0 0 18 7h-1.26a8 8 0 1 0-11.62 9M13 11l-4 6h6l-4 6'
};
const wxPath = (icon) => WX_PATH[icon] || WX_PATH.rain;

const wxIconWord = { sun: 'Sunny', moon: 'Clear', partly: 'Partly cloudy', cloud: 'Cloudy', fog: 'Fog', drizzle: 'Drizzle', rain: 'Rain', snow: 'Snow', storm: 'Storm' };
const deg = (t) => (t == null ? '–' : Math.round(t) + '°');
const capFirst = (s) => (s ? s[0].toUpperCase() + s.slice(1) : '');
const wxTime = (iso) => {
  const d = new Date(iso); if (isNaN(d)) return iso || '';
  const t = new Date(), tm = new Date(t.getFullYear(), t.getMonth(), t.getDate() + 1);
  const day = d.toDateString() === t.toDateString() ? 'today' : d.toDateString() === tm.toDateString() ? 'tomorrow' : d.toLocaleDateString('en-GB', { weekday: 'long' });
  return day + ' ' + d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
};

function weatherView(d, err, st) {
  if (!d) return { ready: false, word: err ? 'Couldn’t load the weather.' : 'Reading the weather…', failed: !!err };
  if (d.off || !d.now) return { ready: false, word: d.off === 'Free' ? 'No weather on Free.' : d.off ? (/^No place/.test(d.off) ? 'No place set yet.' : 'The weather is off.') : d.error ? 'Couldn’t read the weather just now.' : 'Reading the weather…', failed: !!d.error };
  const n = d.now, t = d.today || {};
  const src = d.warn_source || '';
  const m = d.looked ? Math.round((Date.now() / 1000 - d.looked) / 60) : null;
  const mins = (d.minutes || []).slice(0, 24);
  const top = Math.max(1, ...mins.map((x) => x.mm || 0));
  return {
    ready: true, failed: false, word: '',
    temp: deg(n.temp), line: [n.sunny ? 'Sunny' : capFirst(n.text), n.feels != null ? 'feels like ' + deg(n.feels) : '',
      n.wind != null ? 'wind ' + Math.round(n.wind) + ' km/h' + (n.dir ? ' from the ' + n.dir : '') + ' (' + n.bft + ' Bft)' + (n.gusts != null && n.gusts > n.wind + 4 ? ', gusts ' + Math.round(n.gusts) : '') : '',
      n.raining ? 'raining now' : 'rain ' + (n.chance || 0) + '%'].filter(Boolean).join(' · '),
    hours: (d.hours || []).slice(0, 10).map((h) => ({ key: h.at, t: h.at, deg: deg(h.temp), rain: h.chance ? h.chance + '%' : ' ' })),
    radar: d.radar || 'No rain radar right now', radarAt: mins.length ? mins[0].at + ' to ' + mins[mins.length - 1].at : '',
    bars: mins.map((x) => ({ key: x.at, h: Math.round(((x.mm || 0) / top) * 100), c: x.mm ? '#2563eb' : '#cbd5e1' })), hasBars: mins.some((x) => x.mm > 0),
    sunrise: t.sunrise || '–', sunset: t.sunset || '–', uv: n.uv == null ? '–' : Math.round(n.uv * 10) / 10 + (n.uv_word ? ', ' + n.uv_word : ''),
    warnings: (d.warnings || []).map((w, i) => ({ key: i, t: 'Code ' + w.level + (w.what ? ' · ' + w.what : ''),
      line: [w.from ? 'From ' + wxTime(w.from) : '', w.until ? 'until ' + wxTime(w.until) : '', w.area, w.headline].filter(Boolean).join(', ') })),
    noWarn: !(d.warnings || []).length, noWarnLine: /^(KNMI|MeteoAlarm)$/.test(src) ? 'No weather warnings' : 'Weather warnings: ' + (src || 'not read'),
    alertOn: !!(d.alert && d.alert.on), source: 'From Open-Meteo' + (d.radar ? ', Buienradar' : '') + (/^(KNMI|MeteoAlarm)$/.test(src) ? ' and ' + src : '') + (m == null ? '' : ', ' + (m < 1 ? 'just now' : m < 60 ? m + ' minutes ago' : Math.round(m / 60) + ' h ago')),
    place: d.gps ? (d.place && d.place !== 'Your location' ? d.place : 'Where you are') : (d.place || d.home || ''), gps: !!d.gps, home: d.home || '',
    chip: deg(n.temp), icon: n.icon || '', path: wxPath(n.icon), busy: !!st.wxBusy,
    // today and tomorrow: high and low, the rain, the wind's strongest gusts
    days: [['today', 'Today', d.today], ['tomorrow', 'Tomorrow', d.tomorrow]].filter((x) => x[2]).map(([key, name, x]) => ({ key, name, path: wxPath(x.icon),
      text: capFirst(x.text || wxIconWord[x.icon] || ''), temps: deg(x.max) + ' / ' + deg(x.min),
      line: [x.chance != null ? 'rain ' + x.chance + '%' + (x.mm ? ', ' + Math.round(x.mm * 10) / 10 + ' mm' : '') : '', x.gusts != null ? 'gusts up to ' + Math.round(x.gusts) + ' km/h' : ''].filter(Boolean).join(' · ') })),
    hasDays: !!(d.today || d.tomorrow)
  };
}

export function vals(st, ctx, D) {
  const { app, AG, sc } = ctx;
  const say = (t) => app.say(t);
  const isDemo = D === demo;
  const R = isDemo ? null : (D || { err: {} });
  const err = (R && R.err) || {};

  // The design picker: switches the app's design in place, keeping where you are.
  const designs = DESIGNS.map((d) => {
    const on = st.design === d.id;
    return { name: d.name, line: d.line, on: on ? 'true' : 'false', ring: on ? '7px solid #0f172a' : '2px solid #cbd5e1',
      href: '?design=' + d.id, pick: (e) => { if (e && e.preventDefault) e.preventDefault(); app.useDesign(d.id); } };
  });

  // ---- the prototypes' own values (the demo) --------------------------------------------
  const DD = demo;
  const FEAT = DD.features;
  const featRows = FEAT.map((f) => {
    const on = st.feat[f[0]]; const blocked = !!f[3] && !st.feat[f[3]]; const need = f[3] ? FEAT.filter((x) => x[0] === f[3])[0][1] : '';
    return { name: f[1], line: blocked ? 'Needs ' + need + ': turn that on first' : f[2],
      toggle: () => { if (!blocked) app.setState((x) => ({ feat: Object.assign({}, x.feat, { [f[0]]: !x.feat[f[0]] }) })); },
      bg: blocked ? '#e2e8f0' : (on ? '#16a34a' : '#cbd5e1'), just: on && !blocked ? 'flex-end' : 'flex-start', op: blocked ? 0.5 : 1 };
  });
  const featCount = FEAT.filter((f) => st.feat[f[0]] && !(f[3] && !st.feat[f[3]])).length;
  const voiceGroups = ['donna', 'pepper', 'mp'].map((k) => ({ name: AG[k].name, color: AG[k].color, ink: AG[k].ink, initial: AG[k].initial,
    opts: DD.voices[k].map((v) => { const on = st.voices[k] === v; return { v, pick: () => app.setState((x) => ({ voices: Object.assign({}, x.voices, { [k]: v }) })), ring: on ? '7px solid ' + AG[k].color : '2px solid #cbd5e1' }; }) }));
  const placeChips = [['here', 'Where you are'], ['home', 'Home']].map((p) => {
    const on = st.place === p[0];
    return { name: p[1], pick: () => app.setState({ place: p[0] }), bg: on ? '#0f172a' : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });
  const free = sw(st.free), off = sw(st.offline), fresh = sw(st.fresh), rain = sw(st.rain);

  // ---- the tour: the demo's home tour, or a real piece's steps -------------------------
  const agentsList = (R && R.agents && R.agents.agents) || [];
  const nameOf = (id) => ((agentsList.find((a) => a.id === id) || {}).name) || ({ donna: 'Donna', pepper: 'Pepper', moneypenny: 'Moneypenny' })[id];
  const named = (t) => String(t || '').replace(/\{donna\}/g, nameOf('donna')).replace(/\{pepper\}/g, nameOf('pepper')).replace(/\{moneypenny\}/g, nameOf('moneypenny'));
  const T = R && R.tour;
  const realPieces = T && Array.isArray(T.pieces) ? T.pieces.filter((p) => !DROP_PIECES.has(p.id)).map((p) => Object.assign({}, p, { steps: (p.steps || []).filter((s) => !DROP_STEPS.has(p.id + ':' + s.title)) })).filter((p) => p.steps.length) : [];
  const piece = !isDemo && st.tourPiece ? realPieces.find((p) => p.id === st.tourPiece) : null;
  const TOUR = isDemo ? DD.tour : piece ? piece.steps.map((s) => [named(s.title), named(s.text)]) : [];
  // the demo walks home; a real piece walks over the screens its steps open, wherever they are
  const tourOn = isDemo ? st.tour >= 0 && sc === 'home' && TOUR.length > 0 : st.tour >= 0 && TOUR.length > 0;
  const tourStep = tourOn ? TOUR[Math.min(st.tour, TOUR.length - 1)] : ['', ''];
  const finishPiece = () => {
    if (!piece) return;
    const seen = (st.tourSeen || []).includes(piece.id) ? st.tourSeen : (st.tourSeen || []).concat([piece.id]);
    store.set('hq-tour-seen', JSON.stringify(seen));
    app.setState({ tourSeen: seen });
  };
  // A step opens its screen (with its agent's space for her own screens) under the card.
  const stepTo = (p, i) => {
    const step = p.steps[i] || {};
    const patch = { tour: i, tourFound: true };
    if (step.go) {
      patch.screen = step.go;
      patch.stack = step.go === 'home' ? [] : ['home'];
      if (step.space || ['donna', 'pepper', 'mp'].includes(step.go)) patch.space = step.space || step.go;
      if (step.go === 'chat') patch.chatAgent = step.space || 'donna';
    }
    app.setState(patch);
    if (step.go && app.entered) app.entered(step.go);
  };
  const tourNext = isDemo ? () => app.setState((x) => ({ tour: x.tour + 1 >= TOUR.length ? -1 : x.tour + 1 }))
    : () => { if (!piece) return; if (st.tour + 1 >= TOUR.length) { finishPiece(); app.setState({ tour: -1, tourPiece: null, screen: 'tutorial', stack: ['home'] }); } else stepTo(piece, st.tour + 1); };
  const tourBack = isDemo ? () => app.setState((x) => ({ tour: Math.max(0, x.tour - 1) })) : () => { if (piece) stepTo(piece, Math.max(0, st.tour - 1)); };
  const tourClose = isDemo ? () => app.setState({ tour: -1 }) : () => app.setState({ tour: -1, tourPiece: null, screen: 'tutorial', stack: ['home'] });
  const startPiece = (p) => () => { app.setState({ tourPiece: p.id, tour: 0 }); stepTo(p, 0); };
  const pieces = isDemo
    ? DD.pieces.map((p) => ({ n: p[0], t: p[1], done: p[2], start: () => app.setState({ screen: 'home', stack: [], tour: 0 }) }))
    : realPieces.map((p, i) => {
      const seen = (st.tourSeen || []).includes(p.id);
      return { n: seen ? '✓' : String(i + 1), t: named(p.title), line: named(p.line || ''), done: seen ? 'Done' : '', key: p.id, dot: !seen, start: startPiece(p) };
    });
  // The card: which piece and step, its made-up example, the Ask button for the piece's agent, and where it sits.
  const cur = piece ? piece.steps[Math.min(st.tour, piece.steps.length - 1)] || {} : {};
  const askKey = piece ? AGENT_KEY[piece.agent] || PIECE_AGENT[piece.id] || 'donna' : 'donna';
  const askAg = AG[askKey] || AG.donna;
  const demoRows = cur.demo && Array.isArray(cur.demo.items) ? cur.demo.items.map((x, i) => (cur.demo.kind === 'chat'
    ? { key: i, a: x[0] === 'you' ? 'You' : askAg.name, b: named(x[1]) } : { key: i, a: named(x[0]), b: named(x[1]) })) : [];
  const spotOn = tourOn && !isDemo && !!cur.spot && st.tourFound !== false;
  const tourv = {
    on: tourOn, real: !isDemo && tourOn,
    count: isDemo ? 'Home · ' + (st.tour + 1) + ' of ' + TOUR.length : (piece ? named(piece.title) : '') + (TOUR.length > 1 ? ' · ' + (st.tour + 1) + ' of ' + TOUR.length : ''),
    title: tourStep[0], text: tourStep[1], demo: demoRows, hasDemo: demoRows.length > 0,
    soon: !!cur.soon, where: !isDemo && tourOn && cur.spot && st.tourFound === false ? 'It isn’t on this screen right now: it shows up on a call, or it’s switched off in Settings, What HQ helps you with.' : '',
    askName: isDemo ? AG.donna.name : askAg.name, askBg: isDemo ? '#f5f3ff' : askAg.tint, askFg: isDemo ? '#6d28d9' : askAg.accent,
    ask: isDemo ? () => { app.startCall('donna'); app.setState({ demo: true, tour: -1 }); }
      : () => { const id = piece ? piece.id : ''; app.setState({ tour: -1, tourPiece: null }); app.startCall(askKey, { demo: id }); },
    align: st.tourAt === 'top' ? 'flex-start' : 'flex-end', pad: st.tourAt === 'top' ? '72px 16px 16px' : '16px 16px 120px',
    shade: spotOn ? 'transparent' : 'rgba(15,23,42,0.35)', nextLabel: st.tour === TOUR.length - 1 ? 'Done' : 'Next', backOff: st.tour <= 0
  };
  if (!isDemo) placeSpotSoon(app, tourOn && cur.spot ? cur.spot : '', askAg.color);

  // ---- real settings ----------------------------------------------------------------------
  let setv = null;
  if (!isDemo) {
    const items = ((R.features && R.features.items) || []).filter((f) => !f.hidden);
    const freeOnly = !!(R.agents && R.agents.free_only);
    const toggleFeature = (f) => async () => {
      if (f.waiting || f.fixed || st.featBusy) return;
      // At once on screen; the server's answer then corrects it.
      app.setState({ featBusy: f.id });
      put(app, { features: { items: ((R.features && R.features.items) || []).map((x) => (x.id === f.id ? Object.assign({}, x, { on: !f.on }) : x)) } });
      try { const out = await app.api.post('api/features', { id: f.id, on: !f.on }, 'features'); if (out && out.items) put(app, { features: { items: out.items } }); if (out && out.said) say(out.said); }
      catch (e) { say('That didn’t switch. Try again.'); read(app, 'features', 'api/features'); }
      app.setState({ featBusy: '' });
    };
    const rowsOf = items.map((f) => {
      const blocked = !!(f.waiting || f.fixed);
      const line = (f.line || '') + (f.fixed ? ' ' + f.fixed + '.' : f.waiting ? ' Needs ' + f.needs_name + ': turn that on first.' : '') + (f.pieces ? ' ' + f.pieces + '.' : '');
      const on = !!f.on;
      return { key: f.id, name: f.name, line, toggle: toggleFeature(f), bg: blocked ? '#e2e8f0' : (on ? '#16a34a' : '#cbd5e1'), just: on ? 'flex-end' : 'flex-start', op: blocked ? 0.5 : 1, on: on ? 'true' : 'false' };
    });
    const drive = items.find((f) => f.id === 'driving');
    const k = drive && drive.key;
    const saveKey = async (val) => {
      app.setState({ keySaid: '' });
      try {
        const out = await app.api.post('api/drive/key', { key: val }, 'features');
        if (out && out.items) put(app, { features: { items: out.items } });
        app.setState((x) => ({ keySaid: val ? 'Kept on this computer.' : 'Forgotten.', drafts: Object.assign({}, x.drafts, { settingsMapsKey: '' }) }));
      } catch (e) { app.setState({ keySaid: (e.body && e.body.error) || 'Couldn’t keep it. Try again.' }); }
    };
    const ag = (key) => agentsList.find((a) => a.id === ID[key]) || {};
    const voiceOf = (key) => st.voiceIds[key] || ag(key).voice || 'af_heart';
    const voices = ['donna', 'pepper', 'mp'].map((key) => ({ key, name: ag(key).name || AG[key].name, color: AG[key].color, ink: AG[key].ink, initial: (ag(key).name || AG[key].name)[0],
      v: VOICE_NAME[voiceOf(key)] || voiceOf(key), character: firstSentence(ag(key).character || ''), hasCharacter: !!ag(key).character,
      opts: VOICES.map(([id, label]) => ({ key: id, v: label, ring: voiceOf(key) === id ? '7px solid ' + AG[key].color : '2px solid #cbd5e1',
        pick: () => { store.set('hq-voice-' + ID[key], id); app.setState((x) => ({ voiceIds: Object.assign({}, x.voiceIds, { [key]: id }) })); } })) }));
    const dev = R.devices || { can: true, ins: [], outs: [] };
    const mic = devPick('hq-mic'), out = devPick('hq-out');
    const pickDev = (storeKey, d) => () => { store.set(storeKey, d ? JSON.stringify({ id: d.id, label: d.label }) : null); app.setState({ [storeKey === 'hq-mic' ? 'mic' : 'out']: d ? d.id : '' }); };
    const devRows = (list, picked, storeKey, word) => [{ key: 'default', name: 'Default', on: !(picked && picked.id), pick: pickDev(storeKey, null) }]
      .concat(list.map((d, i) => ({ key: d.id, name: d.label || word + ' ' + (i + 1), on: !!(picked && picked.id === d.id), pick: pickDev(storeKey, d) })))
      .map((r) => Object.assign(r, { use: r.on ? 'In use' : '' }));
    const looks = [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']].map(([id, name]) => ({ key: id, name, bg: st.look === id ? '#ffffff' : 'transparent',
      pick: () => { theme.apply(id); app.setState({ look: id }); } }));
    const W = weatherView(R.weather, err.weather, st);
    const wxPick = (here) => async () => {
      if (here) {
        store.set('hq-wx-gps', '1');
        app.setState({ wxBusy: true });
        if (!(await locate())) { store.set('hq-wx-gps', '0'); say('Couldn’t get your location.'); }
      } else { store.set('hq-wx-gps', '0'); wxPos = null; app.setState({ wxBusy: true }); }
      await loadWeather(app, true);
      app.setState({ wxBusy: false });
    };
    const rainAlert = async () => {
      const on = !(R.weather && R.weather.alert && R.weather.alert.on);
      put(app, { weather: Object.assign({}, R.weather, { alert: Object.assign({}, R.weather && R.weather.alert, { on }) }) });
      try { const a = await app.api.post('api/weather/alert', { on }, 'weather'); app.setData(NAME, (o) => Object.assign({}, o, { weather: Object.assign({}, o.weather, { alert: a && a.on !== undefined ? a : Object.assign({}, o.weather.alert, { on }) }) })); }
      catch (e) { say('Couldn’t switch it. Try again.'); loadWeather(app, false); }
    };
    const keepNow = store.get('hq-keep-sound') === 'on', soundNow = store.get('hq-sound') !== 'off';
    const sound = sw(soundNow), rainSw = sw(W.ready && W.alertOn);
    setv = {
      features: rowsOf, featWait: !R.features, featWord: err.features ? 'This couldn’t be read just now.' : 'Looking…', featFailed: !R.features && !!err.features,
      featCount: R.features ? items.filter((f) => f.on).length + ' of ' + items.length + ' on' : '', retryFeatures: () => read(app, 'features', 'api/features'),
      mapsKey: !!(drive && drive.on), keyNote: k && k.key ? 'Your ' + (k.provider_name || 'maps') + ' key is on this computer' + (k.today != null ? ' (' + k.today + ' looks today).' : '.') : 'No key yet: the tutorial shows how to get one.',
      keyHolder: k && k.key ? 'Paste a new key to replace it' : 'Paste your Google Maps or TomTom key', keySave: k && k.key ? 'Replace' : 'Save', hasKey: !!(k && k.key),
      saveKey: () => { const v = ((st.drafts && st.drafts.settingsMapsKey) || '').trim(); if (v) saveKey(v); }, submitKey: (v) => saveKey(v), forgetKey: () => saveKey(''), keySaid: st.keySaid || '',
      voices, looks, freeOnly,
      mics: devRows(dev.ins, mic, 'hq-mic', 'Microphone'), micTitle: IS_PHONE ? 'Microphone and sound' : 'Microphone', canChoose: dev.can, cantChoose: !dev.can,
      outs: devRows(dev.outs, out, 'hq-out', 'Speaker'), showOuts: !IS_PHONE && CAN_SINK && dev.outs.length > 0,
      noOutsLine: IS_PHONE ? (IS_IOS ? 'On an iPhone her voice follows the microphone. You can also switch these in Control Center.' : 'Her voice follows the microphone.') : 'This browser can’t choose where her voice plays: it plays where the computer’s own sound goes.',
      noOuts: IS_PHONE || !CAN_SINK || !dev.outs.length,
      // the browser names the devices only once the page may use the microphone: Show asks once
      askNames: dev.can && !IS_PHONE && dev.ins.length > 0 && !dev.ins.some((d) => d.label) && typeof navigator !== 'undefined' && !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
      showNames: async () => {
        try { const s = await navigator.mediaDevices.getUserMedia({ audio: true }); s.getTracks().forEach((t) => t.stop()); } catch (e) { say('The browser didn’t allow the microphone.'); }
        listDevices(app);
      },
      // on a Mac: whether music and videos turn down during a call (hq-keep-sound, read when a call opens the mic)
      // (read from the device each time, so a pick in the call's own sheet shows here too)
      isMac: IS_MAC && !IS_PHONE, keepWord: keepNow ? 'Normal' : 'Lower',
      keepLine: keepNow ? 'Music and videos stay at their normal volume during a call' : 'Music and videos turn down while you’re on a call',
      toggleKeep: () => { store.set('hq-keep-sound', keepNow ? 'off' : 'on'); app.setState({ keepSound: !keepNow }); },
      soundWord: soundNow ? 'On' : 'Off', toggleSound: () => { store.set('hq-sound', soundNow ? 'off' : 'on'); app.setState({ sound: !soundNow }); }, soundBg: sound.bg, soundJust: sound.just,
      weather: W, wxReady: W.ready, wxWait: !W.ready, wxRetry: () => loadWeather(app, true),
      places: [['here', 'Where you are', true], ['home', 'Home' + (W.home ? ' · ' + W.home : ''), false]].map(([id, name, here]) => {
        const on = W.ready && (here ? W.gps : !W.gps);
        return { key: id, name, pick: wxPick(here), bg: on ? '#0f172a' : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
      }),
      toggleRain: rainAlert, rainBg: rainSw.bg, rainJust: rainSw.just,
      tourWait: !T, tourWord: err.tour ? 'The tutorial couldn’t be read just now.' : 'Looking…'
    };
  }

  const realFree = !isDemo && setv && setv.freeOnly ? true : st.free;
  const W = setv && setv.weather;
  const freshReal = !isDemo && !!(st.data && st.data.mp && st.data.mp.routines && st.data.mp.routines.noLog);

  return {
    agent: {},
    sheets: {},
    submit: { settingsMapsKey: (text) => { if (setv) setv.submitKey(text); } },
    titles: { weather: isDemo ? DD.weatherTitle : W && W.ready && W.place ? 'Weather · ' + W.place : 'Weather' },
    values: {
      designs,
      hours: DD.hours.map((h) => ({ t: h[0], deg: h[1], rain: h[2] || ' ' })),
      toggleRain: () => app.setState((x) => ({ rain: !x.rain })), rainBg: rain.bg, rainJust: rain.just,
      featRows, featCount: isDemo ? featCount + ' of ' + FEAT.length + ' on' : setv.featCount, mapsKey: st.feat.driving && st.feat.travel && st.feat.calendar,
      voiceGroups, placeChips, allOn: () => say('Everything is on'),
      tourOn, tourTitle: tourStep[0], tourText: tourStep[1], tourCount: (st.tour + 1) + ' of ' + TOUR.length, tourNextLabel: st.tour === TOUR.length - 1 ? 'Done' : 'Next',
      tourNext, tourBack, tourClose, tourv,
      pieces, tourDot: !isDemo && !st.tourOpened,
      demoMode: !!app.demoMode,
      offline: st.offline, free: isDemo ? st.free : realFree, fresh: isDemo ? st.fresh : freshReal, notFresh: isDemo ? !st.fresh : !freshReal,
      goOnline: isDemo ? () => app.setState({ offline: false }) : () => app.loadAll(),
      toggleFree: isDemo ? () => app.setState((x) => ({ free: !x.free })) : () => {
        if (setv.freeOnly) { say('This HQ is Free only.'); return; }
        store.set('hq-free', st.free ? 'off' : 'on'); app.setState({ free: !st.free });
      },
      freeBg: isDemo ? free.bg : sw(realFree).bg, freeJust: isDemo ? free.just : sw(realFree).just,
      toggleOffline: () => app.setState((x) => ({ offline: !x.offline })), offBg: off.bg, offJust: off.just,
      toggleFresh: () => app.setState((x) => ({ fresh: !x.fresh })), freshBg: fresh.bg, freshJust: fresh.just,
      ringMe: () => app.setState({ incoming: true }),
      // The weather chip on home (for the core's home templates).
      wxChip: isDemo ? '7°' : W && W.ready ? W.chip : '',
      wxIcon: !isDemo && W && W.ready ? W.path : WX_PATH.rain,
      setv: setv || demoSetv(app, st, voiceGroups, placeChips, featRows, featCount, FEAT.length, rain)
    }
  };
}

// The same shape from the demo module, so the templates draw the demo as the prototypes do.
function demoSetv(app, st, voiceGroups, placeChips, featRows, featCount, total, rain) {
  const D = demo;
  return {
    features: featRows.map((f, i) => Object.assign({ key: D.features[i][0] }, f)), featWait: false, featWord: '', featFailed: false, featCount: featCount + ' of ' + total + ' on',
    retryFeatures: () => {}, mapsKey: !!(st.feat.driving && st.feat.travel && st.feat.calendar), keyNote: 'Once saved: Replace or Forget', keyHolder: 'Paste the key', keySave: 'Save', hasKey: false,
    saveKey: () => {}, submitKey: () => {}, forgetKey: () => {}, keySaid: '',
    voices: voiceGroups.map((g, i) => Object.assign({ key: ['donna', 'pepper', 'mp'][i], v: st.voices[['donna', 'pepper', 'mp'][i]], character: '' }, g, { opts: g.opts.map((o) => Object.assign({ key: o.v }, o)) })),
    looks: [['system', 'System', '#ffffff'], ['light', 'Light', 'transparent'], ['dark', 'Dark', 'transparent']].map(([key, name, bg]) => ({ key, name, bg, pick: () => {} })), freeOnly: false,
    mics: [{ key: 'a', name: 'iPhone microphone', use: 'In use', pick: () => {} }, { key: 'b', name: 'AirPods', use: '', pick: () => {} }], micTitle: 'Microphone', canChoose: true, cantChoose: false,
    outs: [{ key: 'a', name: 'iPhone speaker', use: 'In use', pick: () => {} }, { key: 'b', name: 'AirPods', use: '', pick: () => {} }], showOuts: true,
    noOutsLine: 'On an iPhone you can also switch these in Control Center.', noOuts: true,
    soundWord: 'On', toggleSound: () => {}, soundBg: '#16a34a', soundJust: 'flex-end', askNames: false, showNames: () => {}, isMac: false, keepWord: 'Lower', keepLine: '', toggleKeep: () => {},
    weather: { ready: true, temp: '7°', line: 'Cloudy · feels like 4° · wind 18 km/h from the south-west', hours: D.hours.map((h) => ({ key: h[0], t: h[0], deg: h[1], rain: h[2] || ' ' })),
      radar: 'Rain from about 16:00', radarAt: '16:00', bars: [], hasBars: false, sunrise: '08:21', sunset: '16:36', uv: '1, low', warnings: [], noWarn: true, noWarnLine: 'No weather warnings',
      alertOn: st.rain, source: 'From the national weather service, 5 minutes ago', place: 'Amsterdam', gps: st.place === 'here', home: 'Amsterdam', chip: '7°', busy: false,
      path: WX_PATH.rain, days: [], hasDays: false },
    wxReady: true, wxWait: false, wxRetry: () => {},
    places: placeChips.map((p, i) => Object.assign({ key: i ? 'home' : 'here' }, p)),
    toggleRain: () => app.setState((x) => ({ rain: !x.rain })), rainBg: rain.bg, rainJust: rain.just, tourWait: false, tourWord: ''
  };
}
