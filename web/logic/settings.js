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

export const NAME = 'settings';
export const WIRED = true;
// Settings draw before their data is in: the design picker, Free and the states never wait.
export const LOADING_OK = true;
export { demo };
import { DESIGNS } from './core.js';

export const start = {
  rain: true, offline: false, fresh: false, free: false,
  feat: Object.assign({}, demo.featuresOn), voices: Object.assign({}, demo.voicesPicked), place: 'here', tour: -1,
  voiceIds: {}, sound: true, look: 'system', mic: '', out: '', tourPiece: null, tourSeen: [], featBusy: '', keySaid: '', wxBusy: false
};

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
    look: look === 'light' || look === 'dark' ? look : 'system', tourSeen: json('hq-tour-seen', []) });
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
  tutorial: (app) => read(app, 'tour', 'tour.json')
};

// The tutorial's pieces that still fit the new design (see the report for the others).
const DROP_PIECES = new Set(['news', 'team', 'hours', 'sprint', 'mac']);
const DROP_STEPS = new Set(['notes:Feedback for HQ', 'notes:Connect to the person who makes HQ', 'notes:Invite someone to send you feedback',
  'settings:Light or dark', 'settings:Microphone and sound, quickly', 'call:She takes it away', 'yours:Change it, add to it', 'yours:Coming soon: shared best practices',
  'updates:The version number', 'chat:A quick yes']);

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
      n.wind != null ? 'wind ' + Math.round(n.wind) + ' km/h' + (n.dir ? ' from the ' + n.dir : '') + ' (' + n.bft + ' Bft)' : '',
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
    chip: deg(n.temp), icon: n.icon || '', busy: !!st.wxBusy
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
  const tourOn = st.tour >= 0 && sc === 'home' && TOUR.length > 0;
  const tourStep = tourOn ? TOUR[Math.min(st.tour, TOUR.length - 1)] : ['', ''];
  const finishPiece = () => {
    if (!piece) return;
    const seen = (st.tourSeen || []).includes(piece.id) ? st.tourSeen : (st.tourSeen || []).concat([piece.id]);
    store.set('hq-tour-seen', JSON.stringify(seen));
    app.setState({ tourSeen: seen });
  };
  const tourNext = isDemo ? () => app.setState((x) => ({ tour: x.tour + 1 >= TOUR.length ? -1 : x.tour + 1 }))
    : () => { if (st.tour + 1 >= TOUR.length) { finishPiece(); app.setState({ tour: -1, tourPiece: null }); app.go('tutorial'); } else app.setState({ tour: st.tour + 1 }); };
  const tourClose = isDemo ? () => app.setState({ tour: -1 }) : () => app.setState({ tour: -1, tourPiece: null });
  const pieces = isDemo
    ? DD.pieces.map((p) => ({ n: p[0], t: p[1], done: p[2], start: () => app.setState({ screen: 'home', stack: [], tour: 0 }) }))
    : realPieces.map((p, i) => ({ n: String(i + 1), t: named(p.title), done: (st.tourSeen || []).includes(p.id) ? 'Done' : '', key: p.id,
      start: () => app.setState({ screen: 'home', stack: [], tour: 0, tourPiece: p.id }) }));

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
      v: VOICE_NAME[voiceOf(key)] || voiceOf(key), character: ag(key).character || '',
      opts: VOICES.map(([id, label]) => ({ key: id, v: label, ring: voiceOf(key) === id ? '7px solid ' + AG[key].color : '2px solid #cbd5e1',
        pick: () => { store.set('hq-voice-' + ID[key], id); app.setState((x) => ({ voiceIds: Object.assign({}, x.voiceIds, { [key]: id }) })); } })) }));
    const dev = R.devices || { can: true, ins: [], outs: [] };
    const mic = devPick('hq-mic'), out = devPick('hq-out');
    const pickDev = (storeKey, d) => () => { store.set(storeKey, d ? JSON.stringify({ id: d.id, label: d.label }) : null); app.setState({ [storeKey === 'hq-mic' ? 'mic' : 'out']: d ? d.id : '' }); };
    const devRows = (list, picked, storeKey, word) => [{ key: 'default', name: 'Default', on: !(picked && picked.id), pick: pickDev(storeKey, null) }]
      .concat(list.map((d, i) => ({ key: d.id, name: d.label || word + ' ' + (i + 1), on: !!(picked && picked.id === d.id), pick: pickDev(storeKey, d) })))
      .map((r) => Object.assign(r, { use: r.on ? 'In use' : '' }));
    const looks = [['system', 'System'], ['light', 'Light'], ['dark', 'Dark']].map(([id, name]) => ({ key: id, name, bg: st.look === id ? '#ffffff' : 'transparent',
      pick: () => { store.set('hq-theme', id === 'system' ? null : id); app.setState({ look: id }); } }));
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
    const sound = sw(st.sound), rainSw = sw(W.ready && W.alertOn);
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
      soundWord: st.sound ? 'On' : 'Off', toggleSound: () => { store.set('hq-sound', st.sound ? 'off' : 'on'); app.setState({ sound: !st.sound }); }, soundBg: sound.bg, soundJust: sound.just,
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
      tourNext, tourBack: () => app.setState((x) => ({ tour: Math.max(0, x.tour - 1) })), tourClose,
      pieces,
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
    soundWord: 'On', toggleSound: () => {}, soundBg: '#16a34a', soundJust: 'flex-end',
    weather: { ready: true, temp: '7°', line: 'Cloudy · feels like 4° · wind 18 km/h from the south-west', hours: D.hours.map((h) => ({ key: h[0], t: h[0], deg: h[1], rain: h[2] || ' ' })),
      radar: 'Rain from about 16:00', radarAt: '16:00', bars: [], hasBars: false, sunrise: '08:21', sunset: '16:36', uv: '1, low', warnings: [], noWarn: true, noWarnLine: 'No weather warnings',
      alertOn: st.rain, source: 'From the national weather service, 5 minutes ago', place: 'Amsterdam', gps: st.place === 'here', home: 'Amsterdam', chip: '7°', busy: false },
    wxReady: true, wxWait: false, wxRetry: () => {},
    places: placeChips.map((p, i) => Object.assign({ key: i ? 'home' : 'here' }, p)),
    toggleRain: () => app.setState((x) => ({ rain: !x.rain })), rainBg: rain.bg, rainJust: rain.just, tourWait: false, tourWord: ''
  };
}
