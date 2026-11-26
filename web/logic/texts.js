// The texts area: the chat (texts) with each agent, who you text from home, the list of the
// three chats, the bell (her texts on this phone), a failed text and Try again, past calls and
// reading one. The live transcript of a call is the call area's, not this one.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
//
// The three lines: Donna's (GET direct.json, POST direct/send), Moneypenny's (the same with
// line=team) and Pepper's coaching line (GET api/coaching's thread, POST api/coaching {send}).
// The open chat is read every 3 seconds, the others every 15, and again when the service
// worker says a text came in. A tapped text opens /direct (Donna) or /direct?line=team.
import * as demo from './demo/texts.js';

export const NAME = 'texts';
export const WIRED = true;
export const LOADING_OK = true;
export { demo };

export const start = { chatAgent: 'donna', textTo: 'donna', logAgent: 'donna', textsOn: false, retried: false, txLog: null };

const ORDER = ['donna', 'pepper', 'mp'];
const toBubbles = (arr, ag) => arr.map((b) => (b[0] === 'm'
  ? { t: b[1], align: 'flex-end', bg: '#22c55e', fg: '#052e16', radius: '20px 20px 6px 20px' }
  : { t: b[1], align: 'flex-start', bg: ag.tint, fg: '#0f172a', radius: '20px 20px 20px 6px' }));
const toLines = (arr, ag) => arr.map((b) => (b[0] === 'm'
  ? { who: 'You', t: b[1], nc: '#15803d', fc: '#0f172a', fs: '16px', fw: '500' }
  : { who: ag.name, t: b[1], nc: ag.accent, fc: '#0f172a', fs: '16px', fw: '400' }));

// ---------------------------------------------------------------- days and times

const pad = (n) => String(n).padStart(2, '0');
const dayKey = (t) => new Date(t * 1000).toDateString();
const daysAgo = (t) => {
  const d = new Date(t * 1000), n = new Date();
  return Math.round((new Date(n.getFullYear(), n.getMonth(), n.getDate()) - new Date(d.getFullYear(), d.getMonth(), d.getDate())) / 864e5);
};
// Today, Yesterday, the weekday within a week, else the date (as the old chat's day pill).
function dayWord(t) {
  const days = daysAgo(t), d = new Date(t * 1000);
  if (days === 0) return 'Today';
  if (days === 1) return 'Yesterday';
  if (days > 1 && days < 7) return d.toLocaleDateString([], { weekday: 'long' });
  return d.toLocaleDateString([], { weekday: 'short', day: 'numeric', month: 'short', year: d.getFullYear() === new Date().getFullYear() ? undefined : 'numeric' });
}
const lower = (w) => w.replace(/^(Today|Yesterday)$/, (x) => x.toLowerCase());
const clock = (t) => { const d = new Date(t * 1000); return pad(d.getHours()) + ':' + pad(d.getMinutes()); };
// The time on a chat in the list: the clock today, else the day.
const whenShort = (t) => (daysAgo(t) === 0 ? clock(t) : dayWord(t));
const isoDay = (d) => d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());

// ---------------------------------------------------------------- what stays on this device

// When he last saw each chat: Donna's and Pepper's under the old page's names.
const SEEN = { donna: 'hq-direct-seen', pepper: 'hq-coach-read', mp: 'hq-team-seen' };
const readSeen = (k) => { try { return Number(localStorage.getItem(SEEN[k]) || 0) || 0; } catch (e) { return 0; } };
const writeSeen = (k, at) => { try { localStorage.setItem(SEEN[k], String(at)); } catch (e) { /* private mode */ } };

// ---------------------------------------------------------------- the lines

const LINE = { donna: 'direct.json', mp: 'direct.json?line=team', pepper: 'api/coaching' };

const empty = () => ({ lines: {}, pending: { donna: [], pepper: [], mp: [] }, seen: { donna: readSeen('donna'), pepper: readSeen('pepper'), mp: readSeen('mp') },
  calls: null, callsError: '', log: null, logName: null, logError: '', push: null });

// The thread as this page uses it: {at, from: 'me'|'agent', text, quiet, id}.
function shapeLine(k, d) {
  if (k === 'pepper') {
    if (d && d.off === 'Free') return { msgs: [], off: 'Free is on: none of your files. Turn it off in Settings to see your coaching line.', waiting: false };
    if (d && d.on === false) return { msgs: [], off: 'Life coaching is off. Turn it on in Settings, under What HQ helps you with.', waiting: false };
    return { msgs: ((d && d.thread) || []).map((m) => ({ at: Number(m.at) || 0, from: m.from === 'me' ? 'me' : 'agent', text: m.text || '', id: m.id })), waiting: !!(d && d.waiting) };
  }
  // Without Moneypenny the server answers her line with Donna's: then she has no line here.
  if (k === 'mp' && d && d.line && d.line !== 'team') return { msgs: [], off: 'Moneypenny has no texts on this HQ.', waiting: false };
  const msgs = ((d && d.messages) || []).map((m) => ({ at: Number(m.at) || 0, from: m.from === 'me' ? 'me' : 'agent', text: m.text || '', quiet: !!m.quiet, id: m.id }));
  const last = msgs.filter((m) => !m.quiet).slice(-1)[0]; // her quiet note for herself isn't her answer
  return { msgs, waiting: !!(last && last.from === 'me') };
}

const patch = (app, fn) => app.setData(NAME, (old) => fn(old || empty()));
function putLine(app, k, line) {
  patch(app, (o) => {
    // a text he sent goes from the waiting ones once the thread has it
    const pend = (o.pending[k] || []).filter((p) => p.state !== 'sent' || !line.msgs.some((m) => m.from === 'me' && m.text === p.text && m.at >= p.at - 120));
    return Object.assign({}, o, { lines: Object.assign({}, o.lines, { [k]: line }), pending: Object.assign({}, o.pending, { [k]: pend }) });
  });
}

async function fetchLine(app, k) {
  try {
    const d = await app.api.get(LINE[k]);
    putLine(app, k, Object.assign(shapeLine(k, d), { ok: true, error: '' }));
  } catch (err) {
    patch(app, (o) => {
      const was = o.lines[k];
      return Object.assign({}, o, { lines: Object.assign({}, o.lines, { [k]: Object.assign({ msgs: [], waiting: false }, was || {}, { ok: !!(was && was.ok), error: 'Couldn’t load the texts.' }) }) });
    });
  }
}

async function fetchCalls(app) {
  try {
    const d = await app.api.get('api/calls');
    patch(app, (o) => Object.assign({}, o, { calls: (d && d.calls) || [], callsError: '' }));
  } catch (err) {
    patch(app, (o) => Object.assign({}, o, { callsError: 'Couldn’t load the calls.' }));
  }
}

async function fetchLog(app, name) {
  if (!name) return;
  patch(app, (o) => Object.assign({}, o, { logName: name, logError: '', log: o.log && o.log.name === name ? o.log : null }));
  try {
    const d = await app.api.get('api/calls/' + encodeURIComponent(name));
    patch(app, (o) => (o.logName === name ? Object.assign({}, o, { log: d, logError: '' }) : o));
  } catch (err) {
    patch(app, (o) => (o.logName === name ? Object.assign({}, o, { logError: 'Couldn’t load this call.' }) : o));
  }
  scrollEnd(true); // a past call opens where it ended, like a chat
}

// ---------------------------------------------------------------- where he is (Donna's line only)

// As the old chat: only when he allows his location (the weather's "Use my location", kept as
// hq-wx-gps, or the browser already allows it and he didn't say no), read ahead so sending never waits.
let hereSpot = null;
async function hereOk() {
  if (typeof navigator === 'undefined' || !navigator.geolocation) return false;
  let want = null;
  try { want = localStorage.getItem('hq-wx-gps'); } catch (e) { /* no storage */ }
  if (want === '0' || want === '1') return want === '1';
  try { return (await navigator.permissions.query({ name: 'geolocation' })).state === 'granted'; } catch (e) { return false; }
}
async function readHere() {
  if (!(await hereOk())) { hereSpot = null; return; }
  navigator.geolocation.getCurrentPosition((p) => {
    hereSpot = { lat: p.coords.latitude.toFixed(4), lon: p.coords.longitude.toFixed(4), at: Date.now() };
  }, () => {}, { enableHighAccuracy: true, timeout: 15000, maximumAge: 2 * 60 * 1000 });
}

// ---------------------------------------------------------------- sending

let pendSeq = 0;
const setPending = (app, k, fn) => patch(app, (o) => Object.assign({}, o, { pending: Object.assign({}, o.pending, { [k]: fn(o.pending[k] || []) }) }));

// His text shows at once; it's marked failed (with Try again) when the server didn't take it.
async function send(app, k, text, again) {
  const id = again || ('p' + (++pendSeq));
  const at = Date.now() / 1000;
  setPending(app, k, (list) => (again ? list.map((p) => (p.id === id ? Object.assign({}, p, { state: 'sending', at }) : p)) : list.concat([{ id, text, at, state: 'sending' }])));
  scrollEnd(true);
  try {
    if (k === 'pepper') {
      const d = await app.api.post('api/coaching', { send: text }, 'coaching');
      setPending(app, k, (list) => list.map((p) => (p.id === id ? Object.assign({}, p, { state: 'sent' }) : p)));
      if (d && d.thread) putLine(app, k, Object.assign(shapeLine('pepper', d), { ok: true, error: '' }));
      else await fetchLine(app, k);
    } else {
      const here = k === 'donna' && hereSpot && Date.now() - hereSpot.at < 30 * 60 * 1000 ? { lat: hereSpot.lat, lon: hereSpot.lon } : {};
      await app.api.post('direct/send', Object.assign({ text }, here, k === 'mp' ? { line: 'team' } : {}), 'direct');
      setPending(app, k, (list) => list.map((p) => (p.id === id ? Object.assign({}, p, { state: 'sent' }) : p)));
      await fetchLine(app, k);
    }
    quick(app, k);
  } catch (err) {
    setPending(app, k, (list) => list.map((p) => (p.id === id ? Object.assign({}, p, { state: 'failed' }) : p)));
  }
}
// After a text, look every 3 seconds until her answer is there (at most about 4 minutes).
const quickTimers = {};
function quick(app, k) {
  clearTimeout(quickTimers[k]);
  let tries = 0;
  const look = async () => {
    const line = app.state.data[NAME] && app.state.data[NAME].lines[k];
    if (!line || !line.waiting || ++tries > 80) return;
    await fetchLine(app, k);
    markSeen(app);
    scrollEnd(false);
    quickTimers[k] = setTimeout(look, 3000);
  };
  quickTimers[k] = setTimeout(look, 2500);
}

// ---------------------------------------------------------------- her texts on this phone (push)

const SAY = {
  default: 'Her texts don’t reach your phone yet. Tap the bell to turn them on.',
  denied: 'Notifications are off for HQ. Turn them on in Settings, Notifications, HQ.',
  sw: 'Her texts can’t start on this phone right now. Close HQ and open it again.',
  key: 'HQ has no key for her texts right now. It tries again next time you open this.',
  nosub: 'This phone isn’t signed up for her texts. Tap the bell to fix that.',
  oldkey: 'This phone signed up with an old key, so her texts can’t reach it. Tap the bell to fix that.',
  post: 'HQ can’t reach your phone right now. It tries again next time you open this.',
  check: 'Her texts couldn’t be checked on this phone. It tries again next time you open this.',
  home: 'Add HQ to your home screen to get her texts.'
};
const iPhone = () => typeof navigator !== 'undefined' && /iPhone|iPad/.test(navigator.userAgent);
const standalone = () => typeof navigator !== 'undefined' && (navigator.standalone === true || !!(window.matchMedia && matchMedia('(display-mode: standalone)').matches));

// What this phone sees of her texts, looked at on every open and told to the server, as the old
// page's direct-check.js: it keeps the phone on the list, makes a missing subscription when
// notifications are allowed, and never throws. Each step has a time limit.
const LIMIT = 6000;
const said = (e) => String((e && e.name ? e.name + ': ' : '') + ((e && e.message) || e || '')).slice(0, 160);
const b64 = (s) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - s.length % 4) % 4)), (c) => c.charCodeAt(0));
const timed = (p) => {
  let t;
  const late = new Promise((_, no) => { t = setTimeout(() => no(new Error('no answer in ' + (LIMIT / 1000) + ' seconds')), LIMIT); });
  return Promise.race([p, late]).finally(() => clearTimeout(t));
};
const step = async (r, name, f) => { try { return await timed(f()); } catch (e) { r.errors[name] = said(e); return undefined; } };
const sameKey = (sub, key) => {
  try {
    const raw = sub.options && sub.options.applicationServerKey;
    if (!raw) return null;
    const a = new Uint8Array(raw), b = b64(key);
    return a.length === b.length && a.every((x, i) => x === b[i]);
  } catch (e) { return null; } // this phone doesn't say which key it was made with
};
const worker = (r, reg) => {
  r.registered = !!reg;
  if (!reg) return;
  r.scope = reg.scope || '';
  r.active = reg.active ? reg.active.state || 'active' : '';
  r.waiting = !!(reg.waiting || reg.installing);
};
async function pushLook(app, r, tap) {
  if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) { r.problem = 'nosupport'; return; }
  r.permission = Notification.permission;
  r.controlled = !!navigator.serviceWorker.controller;
  worker(r, await step(r, 'registration', () => navigator.serviceWorker.getRegistration('/')));
  if (r.permission !== 'granted') { r.problem = r.permission; return; }
  const reg = await step(r, 'register', () => navigator.serviceWorker.register('/direct-sw.js', { scope: '/' }));
  if (!reg) { r.problem = 'sw'; return; }
  const ready = await step(r, 'ready', () => navigator.serviceWorker.ready);
  worker(r, ready || reg);
  if (!ready) { r.problem = 'sw'; return; }
  const k = await step(r, 'key', () => app.api.get('/direct/key'));
  const key = k && k.key;
  let sub = await step(r, 'subscription', () => ready.pushManager.getSubscription());
  if (sub) {
    r.subscription = String(sub.endpoint).slice(-14);
    r.keyMatch = key ? sameKey(sub, key) : null;
    // only on his tap: a page that read a wrong key never throws a good subscription away by itself
    if (tap && key && r.keyMatch === false) { await step(r, 'unsubscribe', () => sub.unsubscribe()); sub = null; }
  }
  if (!sub) {
    if (!key) { r.problem = 'key'; return; }
    sub = await step(r, 'subscribe', () => ready.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(key) }));
    if (!sub) { r.problem = 'nosub'; return; } // Safari can want a tap for this: the bell is that tap
    r.made = true;
    r.subscription = String(sub.endpoint).slice(-14);
    r.keyMatch = true;
  }
  const sent = await step(r, 'post', () => app.api.post('/direct/subscribe', { subscription: sub.toJSON(), device: navigator.userAgent }, 'direct'));
  r.posted = !!(sent && sent.ok);
  if (r.keyMatch === false) r.problem = 'oldkey';
  else if (!r.posted) r.problem = 'post';
}
async function pushCheck(app, tap) {
  const r = { kind: 'page', origin: '', page: '', frame: false, top: '', standalone: false, permission: 'none', registered: false,
    scope: '', active: '', waiting: false, controlled: false, subscription: '', keyMatch: null, made: false, posted: false, problem: '', errors: {}, ua: '' };
  try {
    r.origin = location.origin;
    r.page = location.pathname;
    r.frame = window.self !== window.top;
    r.top = (location.ancestorOrigins && location.ancestorOrigins.length) ? location.ancestorOrigins[location.ancestorOrigins.length - 1] : '';
    r.standalone = standalone();
    r.ua = String(navigator.userAgent).slice(0, 120);
    await pushLook(app, r, tap);
  } catch (e) {
    r.errors.check = said(e);
    if (!r.problem) r.problem = 'check';
  }
  try { timed(app.api.post('/direct/report', r, 'direct')).catch(() => {}); } catch (e) { /* the report never matters to the page */ }
  patch(app, (o) => Object.assign({}, o, { push: { problem: r.problem, permission: r.permission } }));
  return r;
}
// The bell: asks for notifications on his tap (the only way a phone asks), then signs the phone up.
async function bell(app) {
  const p = app.state.data[NAME] && app.state.data[NAME].push;
  if (p && p.problem === '') { app.say('Her texts reach this phone.'); return; }
  if (p && p.problem === 'nosupport') { app.say(iPhone() && !standalone() ? SAY.home : 'This browser can’t get her texts.'); return; }
  try { if ('Notification' in window && Notification.permission === 'default') await Notification.requestPermission(); } catch (e) { /* asked */ }
  const r = await pushCheck(app, true);
  if (r.problem === '') app.say('Her texts are on.');
}

// ---------------------------------------------------------------- which chat is in view

// The chat he looks at now: the chat screen, or in Thread the space itself (on the Mac the
// middle always shows the space's conversation, unless a call is open).
function openAgent(app) {
  const st = app.state;
  if (typeof document !== 'undefined' && document.hidden) return null;
  if (st.screen === 'chat') return st.chatAgent;
  if (st.design === 'thread') {
    if (app.device === 'mac') return st.screen === 'call' || st.screen === 'transcript' ? null : st.space;
    if (ORDER.includes(st.screen)) return st.screen;
  }
  return null;
}
function markSeen(app) {
  const k = openAgent(app);
  const D = app.state.data[NAME];
  if (!k || !D || !D.lines[k]) return;
  const msgs = D.lines[k].msgs;
  const at = msgs.length ? msgs[msgs.length - 1].at : 0;
  if (at > (D.seen[k] || 0)) {
    writeSeen(k, at);
    patch(app, (o) => Object.assign({}, o, { seen: Object.assign({}, o.seen, { [k]: at }) }));
  }
}

// Scroll the open chat (or a past call) to its end: on opening, after a text, and when a new
// one comes in while he's near the end.
function scrollEnd(force) {
  if (typeof document === 'undefined' || typeof requestAnimationFrame === 'undefined') return;
  const go = () => {
    const ends = [...document.querySelectorAll('[data-tx-end]')];
    for (const id of ['th-space-text', 'thm-text']) {
      // Thread: the conversation is the box just above the text box's bar
      let el = document.getElementById(id);
      while (el && el.parentElement && !(el.previousElementSibling && getComputedStyle(el.previousElementSibling).overflowY === 'auto')) el = el.parentElement;
      if (el && el.previousElementSibling) ends.push(el.previousElementSibling.lastElementChild || el.previousElementSibling);
    }
    for (const end of ends) {
      let box = end.parentElement;
      while (box && box !== document.body) {
        const oy = getComputedStyle(box).overflowY;
        if ((oy === 'auto' || oy === 'scroll') && box.scrollHeight > box.clientHeight) break;
        box = box.parentElement;
      }
      if (!box || box === document.body) continue;
      if (force || box.scrollHeight - box.scrollTop - box.clientHeight < 120) box.scrollTop = box.scrollHeight;
    }
  };
  requestAnimationFrame(() => requestAnimationFrame(go));
}

// ---------------------------------------------------------------- load and enter

let started = false, lastOpen = null;
const lookAll = (app) => Promise.all(ORDER.map((k) => fetchLine(app, k)));

// A tapped text opens /direct or /direct?line=team: open that chat, then tidy the address.
function openFromAddress(app) {
  if (typeof location === 'undefined' || !/\/direct\/?$/.test(location.pathname)) return;
  const q = new URLSearchParams(location.search);
  const k = q.get('line') === 'team' ? 'mp' : 'donna';
  if (app.state.design === 'thread') app.go(k, { space: k });
  else app.go('chat', { chatAgent: k, space: k });
  q.delete('line');
  try { history.replaceState(null, '', location.pathname.replace(/\/direct\/?$/, '/') + (q.toString() ? '?' + q : '')); } catch (e) { /* the address stays */ }
}

export async function load(app) {
  if (!started) {
    started = true;
    if (!app.state.data[NAME]) app.setData(NAME, empty());
    openFromAddress(app);
    readHere();
    if (typeof document !== 'undefined') document.addEventListener('visibilitychange', () => { if (!document.hidden) readHere(); });
    // the service worker tells the page when a pushed text came in
    if (typeof navigator !== 'undefined' && navigator.serviceWorker) navigator.serviceWorker.addEventListener('message', () => lookAll(app).then(() => { markSeen(app); scrollEnd(false); }));
    // The open chat every 3 seconds (as the old chat page), the other two every 15 (as the old dot).
    let tick = 0;
    setInterval(() => {
      if (app.demoMode || (typeof document !== 'undefined' && document.hidden)) return;
      tick++;
      const k = openAgent(app);
      const moved = k !== lastOpen; // another chat came into view without a screen change (Thread on the Mac)
      lastOpen = k;
      if (k) fetchLine(app, k).then(() => { markSeen(app); scrollEnd(moved); });
      if (tick % 5 === 0) ORDER.filter((x) => x !== k).forEach((x) => fetchLine(app, x));
    }, 3000);
    // her texts on this phone: looked at once on every open, never inside the Mac app (it shows her texts itself)
    if (typeof location !== 'undefined' && !new URLSearchParams(location.search).has('app')) pushCheck(app, false);
  }
  await Promise.all([lookAll(app), fetchCalls(app)]);
  markSeen(app);
  scrollEnd(true);
}

const onOpenChat = (app) => { const k = openAgent(app); scrollEnd(true); if (k) fetchLine(app, k).then(() => { markSeen(app); scrollEnd(true); }); };
export const enter = {
  chat: onOpenChat, donna: onOpenChat, pepper: onOpenChat, mp: onOpenChat, home: onOpenChat,
  pastCalls: (app) => fetchCalls(app),
  callLog: (app) => fetchLog(app, app.state.txLog)
};

// ---------------------------------------------------------------- the values

// The demo, as the prototypes show it. The tx… values are this area's additions to the
// design's holes; in the demo they give what the design showed.
function demoVals(st, ctx, D) {
  const { app, AG, sa } = ctx;
  const say = (t) => app.say(t);
  const cha = AG[st.chatAgent];
  const textChips = ORDER.map((k) => {
    const on = st.textTo === k;
    return { name: AG[k].name, on: on ? 'true' : 'false', pick: () => app.setState({ textTo: k }),
      bg: on ? AG[k].color : '#ffffff', fg: on ? AG[k].ink : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });
  const pastCalls = D.pastCalls[st.space].map((d) => ({ day: d.day, items: d.items.map((c) => ({ time: c[0], about: c[1], lines: c[2], open: () => app.go('callLog') })) }));
  const chatList = ORDER.map((k) => {
    const arr = D.texts[k]; const last = arr[arr.length - 1]; const cur = st.space === k; const unread = D.unread[k];
    return { name: AG[k].name, initial: AG[k].initial, color: AG[k].color, ink: AG[k].ink, accent: AG[k].accent, preview: last[1], time: D.lastText[k],
      tc: unread ? AG[k].accent : '#55555c', unread, hasUnread: unread > 0, current: cur ? 'true' : 'false',
      bg: cur ? AG[k].color : 'transparent', fg: cur ? AG[k].ink : '#111114', faceBg: cur ? '#ffffff' : AG[k].color, faceFg: cur ? AG[k].color : AG[k].ink,
      open: () => app.go(k, { space: k }), call: () => app.startCall(k) };
  });
  const showFailed = st.chatAgent === D.failedIn && !st.retried;
  const retry = () => { app.setState({ retried: true }); say('Sent'); };
  const nothing = () => {};
  return {
    agent: { donna: { rows: D.rows } },
    submit: { textsChat: nothing, textsHome: nothing, textsSpace: nothing }, // typing doesn't send in the demo
    values: {
      // `chat` is shared with the call area, which adds chat.call (the live transcript)
      chat: { space: () => app.go('chat', { chatAgent: st.space }), textTo: () => app.go('chat', { chatAgent: st.textTo }) },
      cha, tt: AG[st.textTo], textChips,
      bubbles: toBubbles(D.texts[st.chatAgent], cha).map((b) => Object.assign(b, { txText: true })),
      spaceBubbles: toBubbles(D.texts[st.space], sa), chatList,
      textsOff: !st.textsOn, toggleTexts: () => app.setState((x) => ({ textsOn: !x.textsOn })),
      bellBtnBg: st.textsOn ? cha.tint : '#ffffff', bellBtnFg: st.textsOn ? cha.accent : '#0f172a', bellAria: st.textsOn ? 'Her texts are on. Turn them off' : 'Turn her texts on',
      showFailed, retry,
      pastCalls, logBubbles: toLines(D.pastCallLog, sa),
      txFirstDay: 'Texts · today', txPushLine: SAY.default, txLine: '', txLineOn: false, txReload: nothing, txReloadOn: false,
      txFailed: showFailed ? [{ t: 'Can you book the car wash too?', retry }] : [], txSendChat: nothing,
      txCallsLine: '', txCallsLineOn: false, txLogLength: '4 minutes', txLogLine: '', txLogLineOn: false, continueCall: () => app.startCall(st.space)
    }
  };
}

// Bubbles for one agent's chat, the design's colours. withPills: a day pill item between days
// (the chat screen); without, a day is a small centred bubble (Thread's conversation).
function bubblesFor(k, D, ag, withPills) {
  const line = D.lines[k];
  const msgs = line ? line.msgs : [];
  const pend = (D.pending[k] || []).filter((p) => p.state !== 'failed');
  const out = [];
  let lastDay = '';
  const first = msgs.length ? msgs[0].at : (pend[0] ? pend[0].at : 0);
  const firstDay = first ? dayKey(first) : '';
  const pill = (at) => {
    const dk = dayKey(at);
    if (dk === lastDay) return;
    lastDay = dk;
    if (dk === firstDay && withPills) return; // the chat screen's first day is the pill above the list
    if (dk === firstDay && daysAgo(at) === 0) return; // Thread's list starts under its own Today
    out.push(withPills ? { txPill: dayWord(at) } : { t: dayWord(at), align: 'center', bg: '#f2f2f5', fg: '#55555c', radius: '10px' });
  };
  const mine = (t) => ({ t, align: 'flex-end', bg: '#22c55e', fg: '#052e16', radius: '20px 20px 6px 20px', txText: true });
  for (const m of msgs) {
    pill(m.at);
    out.push(m.from === 'me' ? mine(m.text)
      : { t: m.text, align: 'flex-start', bg: m.quiet ? 'transparent' : ag.tint, fg: m.quiet ? '#64748b' : '#0f172a', radius: '20px 20px 20px 6px', txText: true });
  }
  for (const p of pend) { pill(p.at); out.push(mine(p.text)); }
  return out;
}

function realVals(st, ctx, D0) {
  const { app, AG, sa } = ctx;
  const D = D0 || empty();
  const cha = AG[st.chatAgent];
  const lineOf = (k) => D.lines[k];
  const msgsOf = (k) => (lineOf(k) ? lineOf(k).msgs : []);
  const unreadOf = (k) => msgsOf(k).filter((m) => m.from === 'agent' && !m.quiet && m.at > (D.seen[k] || 0)).length;
  const lastOf = (k) => msgsOf(k).filter((m) => !m.quiet).slice(-1)[0];
  const pendOf = (k) => D.pending[k] || [];

  // A text from the box on home or in a space: sent, and her chat opens.
  const sendFrom = (box, k) => {
    const text = ((app.state.drafts || {})[box] || '').trim();
    if (text) { app.setState((x) => ({ drafts: Object.assign({}, x.drafts, { [box]: '' }) })); send(app, k, text); }
  };
  const openChat = (k) => (st.design === 'thread' ? app.go(k, { space: k }) : app.go('chat', { chatAgent: k, space: k }));

  const textChips = ORDER.map((k) => {
    const on = st.textTo === k;
    return { name: AG[k].name, on: on ? 'true' : 'false', pick: () => app.setState({ textTo: k }),
      bg: on ? AG[k].color : '#ffffff', fg: on ? AG[k].ink : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });

  const chatList = ORDER.map((k) => {
    const last = lastOf(k); const cur = st.space === k; const unread = unreadOf(k); const line = lineOf(k);
    return { name: AG[k].name, initial: AG[k].initial, color: AG[k].color, ink: AG[k].ink, accent: AG[k].accent,
      preview: last ? last.text : (line ? (line.off || (line.error && !line.ok ? line.error : 'No texts yet')) : ''), time: last ? whenShort(last.at) : '',
      tc: unread ? AG[k].accent : '#55555c', unread, hasUnread: unread > 0, current: cur ? 'true' : 'false',
      bg: cur ? AG[k].color : 'transparent', fg: cur ? AG[k].ink : '#111114', faceBg: cur ? '#ffffff' : AG[k].color, faceFg: cur ? AG[k].color : AG[k].ink,
      open: () => app.go(k, { space: k }), call: () => app.startCall(k) };
  });

  // The open chat
  const line = lineOf(st.chatAgent);
  const failed = pendOf(st.chatAgent).filter((p) => p.state === 'failed').map((p) => ({ t: p.text, retry: () => send(app, st.chatAgent, p.text, p.id) }));
  const msgs = msgsOf(st.chatAgent);
  const firstAt = msgs.length ? msgs[0].at : (pendOf(st.chatAgent)[0] || {}).at;
  const txFirstDay = 'Texts · ' + (firstAt ? lower(dayWord(firstAt)) : 'today');
  let txLine = '';
  if (!line) txLine = 'Loading…';
  else if (line.error && !line.ok) txLine = line.error;
  else if (line.off) txLine = line.off;
  else if (!msgs.length && !pendOf(st.chatAgent).length) txLine = 'No texts yet.';

  // The bell: her texts on this phone
  const push = D.push;
  const on = !!push && push.problem === '';
  let txPushLine = '';
  if (push && !on) txPushLine = push.problem === 'nosupport' ? (iPhone() && !standalone() ? SAY.home : '') : (SAY[push.problem] || SAY.check);

  // Past calls in this space, newest first, by day (calls from before the three were Donna's)
  const mineCall = (c, k) => c.agent === AG[k].name || (!c.agent && k === 'donna');
  const herCalls = (D.calls || []).filter((c) => mineCall(c, st.space));
  const today = new Date(), yday = new Date(today); yday.setDate(today.getDate() - 1);
  const pastCalls = [];
  for (const c of herCalls) {
    const day = c.date === isoDay(today) ? 'Today' : c.date === isoDay(yday) ? 'Yesterday' : String(c.started || c.date).split(',')[0];
    let d = pastCalls[pastCalls.length - 1];
    if (!d || d.day !== day) { d = { day, items: [] }; pastCalls.push(d); }
    d.items.push({ time: c.time, about: c.continues ? 'Went on from an earlier call' : 'A call with ' + (c.agent || AG.donna.name), lines: c.said,
      open: () => app.go('callLog', { txLog: c.name }) });
  }
  let txCallsLine = '';
  if (D.calls == null) txCallsLine = D.callsError || 'Loading…';
  else if (!herCalls.length) txCallsLine = D.callsError || 'No calls yet';

  // One past call, as the chat showed it: his lines, hers, her waiting lines, taken-back ones struck through
  const log = D.log && D.log.name === st.txLog ? D.log : null;
  const agentByName = (n) => ORDER.map((k) => AG[k]).find((a) => a.name === n);
  const logAg = (log && agentByName(log.agent)) || sa;
  const logBubbles = log ? (log.lines || []).filter((l) => l.text).map((l) => {
    if (l.who !== 'hq' && l.who !== 'filler') return { who: 'You', t: l.text, nc: '#15803d', fc: l.cancelled ? '#94a3b8' : '#0f172a', fs: '16px', fw: '500', deco: l.cancelled ? 'line-through' : 'none' };
    const who = agentByName(l.agent) || logAg;
    if (l.who === 'filler') return { who: who.name, t: l.text, nc: who.accent, fc: '#64748b', fs: '14px', fw: '400', deco: 'none' };
    return { who: who.name, t: l.text, nc: who.accent, fc: '#0f172a', fs: '16px', fw: '400', deco: 'none' };
  }) : [];
  let txLogLength = '…';
  if (log) {
    const ts = (log.lines || []).map((l) => /^(\d\d?):(\d\d)$/.exec(l.at || l.time || '')).filter(Boolean).map((m) => Number(m[1]) * 60 + Number(m[2]));
    let mins = ts.length ? ts[ts.length - 1] - ts[0] : 0;
    if (mins < 0) mins += 24 * 60;
    txLogLength = mins < 1 ? 'under a minute' : mins === 1 ? '1 minute' : mins + ' minutes';
  }
  let txLogLine = '';
  if (!log) txLogLine = D.logError || 'Loading…';
  else if (!logBubbles.length) txLogLine = 'Nothing said';
  // Continue: only off a call, never as Free (as the old page); the call area starts it
  const continueCall = () => {
    if (!log) return;
    if (st.onCall) { app.say('You’re on a call. Hang up first to continue this one.'); return; }
    if (st.free) { app.say('Free is on. Turn it off in Settings to continue a call.'); return; }
    const k = ORDER.find((x) => AG[x].name === log.agent) || st.space;
    app.startCall(k, { continue: log.name });
  };

  // The rows in each space: her texts and her past calls
  const textsValue = (k) => {
    const n = unreadOf(k);
    if (n) return n + ' new';
    const todayN = msgsOf(k).filter((m) => !m.quiet && daysAgo(m.at) === 0).length;
    if (todayN) return todayN + ' today';
    const last = lastOf(k);
    return last ? dayWord(last.at) : (lineOf(k) ? 'None yet' : '');
  };
  const callsValue = (k) => {
    if (!D.calls) return '';
    const c = D.calls.find((x) => mineCall(x, k));
    if (!c) return 'None yet';
    const d = new Date(c.date + 'T12:00:00');
    return 'Last ' + (isNaN(d) ? c.date : lower(dayWord(d.getTime() / 1000)));
  };
  const rows = (k, label) => ({ pastCalls: ['Past calls', callsValue(k), 'pastCalls'], texts: [label, textsValue(k), st.design === 'thread' ? [k, { space: k }] : ['chat', { chatAgent: k }]] });

  return {
    agent: { donna: { rows: rows('donna', 'Texts') }, pepper: { rows: rows('pepper', 'Coaching line') }, mp: { rows: rows('mp', 'Texts') } },
    submit: {
      textsChat: (text) => send(app, st.chatAgent, text),
      textsHome: (text) => { send(app, st.textTo, text); openChat(st.textTo); },
      textsSpace: (text) => send(app, st.space, text)
    },
    values: {
      chat: { space: () => { sendFrom('textsSpace', st.space); openChat(st.space); }, textTo: () => { sendFrom('textsHome', st.textTo); openChat(st.textTo); } },
      cha, tt: AG[st.textTo], textChips,
      bubbles: bubblesFor(st.chatAgent, D, cha, true), spaceBubbles: bubblesFor(st.space, D, sa, false), chatList,
      textsOff: !!txPushLine, toggleTexts: () => bell(app),
      bellBtnBg: on ? cha.tint : '#ffffff', bellBtnFg: on ? cha.accent : '#0f172a', bellAria: on ? 'Her texts are on' : 'Turn her texts on',
      showFailed: failed.length > 0, retry: () => { if (failed[0]) failed[0].retry(); },
      pastCalls, logBubbles,
      txFirstDay, txPushLine, txLine, txLineOn: !!txLine, txReload: () => fetchLine(app, st.chatAgent), txReloadOn: !!(line && line.error && !line.ok),
      txFailed: failed, txSendChat: () => sendFrom('textsChat', st.chatAgent),
      txCallsLine, txCallsLineOn: !!txCallsLine, txLogLength, txLogLine, txLogLineOn: !!txLogLine, continueCall
    }
  };
}

export function vals(st, ctx, D) {
  return ctx.app.demoMode || !WIRED ? demoVals(st, ctx, D) : realVals(st, ctx, D);
}
