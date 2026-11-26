// The call area: the call mode (it stays on wherever you go), the live transcript of the
// call, the mini bar, an incoming call, bring someone in, take that back, call me back,
// voice off, the demo-call and call-line-down banners. Texts with an agent are not here.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
//
// Starting a call from any area: app.startCall(agent, about)
//   agent  'donna', 'pepper' or 'mp' (the server's 'moneypenny' works too)
//   about  optional, what goes with the call to /api/offer:
//          { about: '<appointment id>' } | { about_todo: '<item id>' } | { about_coaching: '<layer or check-in key>' }
//          | { about_news: '…' } | { continue: '<past call name>', handover?: true, callback?: true }
//          | { ring: '<n>' } | { demo: '<tutorial topic, or empty>' }
// A Free call (Settings) or a demo call never carries the about or continue parts, as on the old page.
// In demo mode (?demo=1) a call is the prototypes' made-up one: nothing is opened or sent.
//
// A real call: the microphone, one RTCPeerConnection without outside servers, one data channel
// "chat" (her states, the lines said, take that back, she hangs up, hands over, calls back, someone
// joins), her voice on an <audio> outside the templates, so it keeps playing on every screen and
// through a design or device switch.
import * as demo from './demo/call.js';
import { rich } from '../engine.js';

export const NAME = 'call';
export const WIRED = true;
export const LOADING_OK = true; // the call works before /api/agents has answered
export { demo };

export const start = {
  onCall: false, callAgent: 'donna', phase: 0, confirmHang: false, muted: false,
  yes: null, voiceOn: true, second: null, takenBack: false, incoming: false, demo: false,
  // the real call (not used in demo mode)
  cs: 'idle', orb: 'listening', cLines: [], cPanel: [], cStarted: 0, cNow: 0, cMsg: '', cAgain: false, cLineDown: false,
  cCancel: false, cHold: false, cTrans: false, cUntapped: false, cAnswered: -1, cRing: null, cFree: false, cLabel: '',
  cSeen: 0, cCxAsk: false, cEnded: null, cDev: 0
};

const PHASES = ['Calling…', 'Your turn', 'Listening…', 'Thinking…', 'Speaking'];
const RINGS = [4, 6, 18, 10, 26];
const ORDER = ['donna', 'pepper', 'mp'];

// The real call: what each of her states says and how wide its ring is.
const ORB = { connecting: ['Calling…', 4], listening: ['Your turn', 6], hearing: ['Listening…', 18], waiting: ['Listening…', 18],
  transcribing: ['Transcribing…', 12], thinking: ['Thinking…', 10], speaking: ['Speaking', 26] };
const SRV = { donna: 'donna', pepper: 'pepper', mp: 'moneypenny' };
const APP = { donna: 'donna', pepper: 'pepper', moneypenny: 'mp', mp: 'mp' };
const NAMES = { donna: 'Donna', pepper: 'Pepper', mp: 'Moneypenny' };
const HOLD_MS = 350, CANCEL_LINGER_MS = 20000, TYPED_MAX = 10000, RETRY_MS = 5000;

const ls = {
  get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* private mode */ } }
};
const pick = (k) => { try { return JSON.parse(ls.get(k) || 'null'); } catch (e) { return null; } };
const two = (n) => String(n).padStart(2, '0');
const clock = (ms) => { const d = new Date(ms); return two(d.getHours()) + ':' + two(d.getMinutes()); };

// Everything of the live call that isn't render state. One call at a time.
const rt = { pc: null, dc: null, stream: null, audio: null, ping: null, tickT: null, audioCtx: null, wake: null,
  secT: null, holdT: null, pressId: null, holding: false, wasMuted: false, tapUsed: false, linger: null, cancellable: false,
  retryT: null, talkGate: null, turn: 0, hooked: false, opts: null, startedOnce: false,
  devList: [], micKey: '', outKey: '', micSwap: 0, btFixing: false, cancelSince: 0, endHow: '' };

function audioEl() {
  if (!rt.audio) {
    rt.audio = document.createElement('audio');
    rt.audio.autoplay = true; rt.audio.setAttribute('playsinline', ''); rt.audio.hidden = true;
    document.body.appendChild(rt.audio);
  }
  return rt.audio;
}
function startAudio() {
  try {
    if (!rt.audioCtx) rt.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    if (rt.audioCtx.state === 'suspended') rt.audioCtx.resume();
  } catch (e) { rt.audioCtx = null; }
}
// The soft tick while she thinks (Settings' thinking sound, hq-sound), silent with her voice off.
function tick() {
  const c = rt.audioCtx; if (!c) return;
  const t = c.currentTime, o = c.createOscillator(), g = c.createGain();
  o.type = 'sine'; o.frequency.setValueAtTime(1100, t); o.frequency.exponentialRampToValueAtTime(700, t + 0.06);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.08, t + 0.005); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.08);
  o.connect(g).connect(c.destination); o.start(t); o.stop(t + 0.1);
}
function thinking(on, st) {
  const want = on && ls.get('hq-sound') !== 'off' && st.voiceOn && st.cs === 'live' && rt.audioCtx;
  if (want && !rt.tickT) { tick(); rt.tickT = setInterval(tick, 900); }
  if (!want && rt.tickT) { clearInterval(rt.tickT); rt.tickT = null; }
}
function applyVoice(on) {
  const a = rt.audio; if (!a) return;
  a.muted = !on;
  const s = a.srcObject;
  if (s && s.getAudioTracks) s.getAudioTracks().forEach((t) => { t.enabled = on; });
}
// ---------------------------------------------------------------- microphone and sound
// Which mic the call listens with and, where the browser can (setSinkId), where her voice plays: chosen
// in Settings or during the call (the call's Microphone and sound sheet), kept on this device by id and
// name (hq-mic, hq-out); a choice that isn't here falls back to Default. The iPhone (any browser there)
// decides the mic and sound itself; WebKit keeps one mic open at a time, so the old one is let go first.
// On the Mac, other sound can stay at its normal volume during a call (hq-keep-sound): the mic is then
// opened without echo cancelling, unless her voice plays through the MacBook's own speakers. With the mic
// on Default and Bluetooth headphones on, the call listens with the MacBook's own mic, so the headphones
// keep their full sound; in the HQ app the sound is bounced once to the speakers and back when their mic
// was opened anyway.
const UA = typeof navigator === 'undefined' ? '' : (navigator.userAgent || '');
const IS_IOS = /iPhone|iPad|iPod/.test(UA) || (/Macintosh/.test(UA) && typeof navigator !== 'undefined' && navigator.maxTouchPoints > 1);
const ONE_MIC = IS_IOS || (/AppleWebKit/.test(UA) && !/Chrome|Chromium|Edg/.test(UA));
const IS_PHONE = IS_IOS || /Android.*Mobile|Mobile.*Android/.test(UA)
  || (typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches && !matchMedia('(any-pointer: fine)').matches);
const IS_MAC = /Macintosh/.test(UA) && !IS_IOS;
const CAN_SINK = typeof HTMLMediaElement !== 'undefined' && 'setSinkId' in HTMLMediaElement.prototype;
const BT = /AirPods|Bluetooth|Buds|Beats|Headphones|Headset|Hands-?Free|Bose|Sony WH|Sony WF|WH-1000|WF-1000|Jabra|Jaybird|Powerbeats|Sennheiser|Shokz|AfterShokz/i;
const OWN_MIC = /MacBook.*Microphone|Built-in Microphone|Internal Microphone|iMac Microphone/i;
const OWN_SPK = /MacBook.*Speakers|Built-in Output|Internal Speakers|iMac Speakers/i;
const devOf = (kind) => (rt.devList || []).filter((d) => d.kind === kind && d.deviceId && d.deviceId !== 'default' && d.deviceId !== 'communications');
const devFind = (list, p) => ((p && p.id) ? (list.find((d) => d.deviceId === p.id) || (p.label && list.find((d) => d.label === p.label)) || null) : null);
const defDev = (kind) => (rt.devList || []).find((d) => d.kind === kind && d.deviceId === 'default') || (rt.devList || []).find((d) => d.kind === kind) || null;
const ownMic = () => devOf('audioinput').find((d) => OWN_MIC.test(d.label || '') && !BT.test(d.label || '')) || null;
const baseName = (l) => String(l || '').replace(/^(Default|Communications) - /, '').replace(/\s*\(.*\)\s*$/, '').trim();
const keepSound = () => ls.get('hq-keep-sound') === 'on';
function btOn() {
  const o = defDev('audiooutput'), i = defDev('audioinput');
  return !!((o && BT.test(o.label || '')) || (i && BT.test(i.label || '')));
}
// Where her voice goes: the output the computer already plays on stays on the default path (a named
// output plays a call's voice much quieter in Chrome on the Mac). On a phone it follows the mic.
function sinkFor() {
  const d = IS_PHONE ? null : devFind(devOf('audiooutput'), pick('hq-out'));
  if (!d) return { id: '', d: null };
  const def = (rt.devList || []).find((x) => x.kind === 'audiooutput' && x.deviceId === 'default');
  const isDef = def && ((d.groupId && d.groupId === def.groupId) || (!!d.label && baseName(def.label) === baseName(d.label)));
  return { id: isDef ? '' : d.deviceId, d };
}
function onSpeakers() { const { d } = sinkFor(), o = d || defDev('audiooutput'); return !!(o && OWN_SPK.test(o.label || '')); }
async function listDevices(app) {
  try { rt.devList = navigator.mediaDevices && navigator.mediaDevices.enumerateDevices ? await navigator.mediaDevices.enumerateDevices() : []; } catch (e) { rt.devList = []; }
  if (app) app.setState((x) => ({ cDev: (x.cDev || 0) + 1 }));
}
function applySink() {
  rt.outKey = (pick('hq-out') || {}).id || '';
  const a = rt.audio; if (!CAN_SINK || !a) return;
  const { id } = sinkFor();
  const moved = a.sinkId !== id;
  try {
    a.setSinkId(id).then(() => {
      // a new output gets a fresh start of her voice on it, at full volume
      a.volume = 1;
      if (moved && a.srcObject) { const s = a.srcObject; a.srcObject = null; a.srcObject = s; a.play().catch(() => {}); }
    }).catch(() => {});
  } catch (e) { /* this browser can't */ }
  try { if (rt.audioCtx && rt.audioCtx.setSinkId) rt.audioCtx.setSinkId(id).catch(() => {}); } catch (e) { /* nor here */ }
}
// What the call's mic asks for: the chosen mic exactly, else the default (see above for the Mac).
function micAudio(chosen) {
  const raw = IS_MAC && !IS_PHONE && keepSound() && !onSpeakers();
  const a = raw ? { echoCancellation: false, noiseSuppression: false, autoGainControl: false }
    : { echoCancellation: true, noiseSuppression: true, autoGainControl: true };
  const p = chosen && pick('hq-mic');
  if (!p || !p.id) {
    const own = chosen && IS_MAC && !IS_PHONE && btOn() ? ownMic() : null;
    return own ? Object.assign({}, a, { deviceId: { exact: own.deviceId } }) : a;
  }
  const d = devFind(devOf('audioinput'), p);
  return Object.assign({}, a, { deviceId: { exact: d ? d.deviceId : p.id } });
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const trackDev = (t) => { let id = ''; try { id = (t.getSettings && t.getSettings().deviceId) || ''; } catch (e) { /* none */ } return { id, label: (t && t.label) || '' }; };
// A new mic chosen on a call takes over at once: opened, sent in place of the old one (no new connection,
// the call goes on), the old one stopped. Muted stays muted, a hold stays a hold. Afterwards the page checks
// which mic it really got and whether it sends any sound, and says so when not.
async function switchMic(app) {
  rt.micKey = ((pick('hq-mic') || {}).id || '') + '|' + keepSound();
  const pc = rt.pc, old = rt.stream;
  if (!pc || !old || app.state.cs !== 'live') return;
  const n = ++rt.micSwap, oldT = old.getAudioTracks()[0];
  const sender = pc.getSenders().find((x) => !x.track || x.track.kind === 'audio');
  if (!sender) return;
  const was = old.getAudioTracks().some((x) => x.enabled), before = oldT ? trackDev(oldT) : { id: '', label: '' };
  const say = (m) => app.setState({ cMsg: m, cAgain: false });
  if (app.state.cMsg) app.setState({ cMsg: '' });
  let fresh = null, back = false;
  if (ONE_MIC) old.getTracks().forEach((x) => x.stop());
  try { fresh = await navigator.mediaDevices.getUserMedia({ audio: micAudio(true) }); }
  catch (e) {
    if (!ONE_MIC) { say('That microphone couldn’t be opened, so the call keeps the one it had.'); return; }
    const a = micAudio(false);
    try { fresh = await navigator.mediaDevices.getUserMedia({ audio: before.id ? Object.assign({}, a, { deviceId: { exact: before.id } }) : a }); }
    catch (e2) { try { fresh = await navigator.mediaDevices.getUserMedia({ audio: a }); } catch (e3) { fresh = null; } }
    if (!fresh) { say('No microphone could be opened. Hang up and call again.'); return; }
    back = true;
  }
  const t = fresh.getAudioTracks()[0];
  if (n !== rt.micSwap || !t || rt.stream !== old || !rt.pc) { fresh.getTracks().forEach((x) => x.stop()); return; }
  t.enabled = was;
  try { await sender.replaceTrack(t); }
  catch (e) { fresh.getTracks().forEach((x) => x.stop()); say('The call couldn’t switch microphones, so it keeps the one it had.'); return; }
  if (rt.stream !== old) { fresh.getTracks().forEach((x) => x.stop()); return; }
  rt.stream = fresh; if (!ONE_MIC) old.getTracks().forEach((x) => x.stop());
  await listDevices(app);
  if (back) { say('That microphone couldn’t be opened, so the call went back to the one it had.'); return; }
  const want = devFind(devOf('audioinput'), pick('hq-mic')), got = trackDev(t);
  const same = (x, y) => (x.label && y.label ? baseName(x.label) === baseName(y.label) : !x.id || x.id === y.deviceId);
  if (want && (got.id || got.label) && !same(got, want)) {
    const kept = got.label ? baseName(got.label) : 'the microphone it had';
    say(IS_IOS ? 'The iPhone kept ' + kept + ': during a call iOS picks the microphone itself. Change it in Control Center.'
      : 'The browser kept ' + kept + '. Hang up, pick the microphone, and call again.');
    return;
  }
  // a mic that opens but sends nothing at all (no sound energy in three seconds, while not muted)
  const energy = async () => { let e = null; try { (await pc.getStats(sender.track)).forEach((r) => { if (r.type === 'media-source' && typeof r.totalAudioEnergy === 'number') e = r.totalAudioEnergy; }); } catch (x) { /* none */ } return e; };
  const e0 = pc.getStats ? await energy() : null;
  if (e0 === null) return;
  await sleep(3000);
  if (n !== rt.micSwap || rt.stream !== fresh || !rt.pc || !t.enabled) return;
  const e1 = await energy();
  if (t.readyState === 'ended' || t.muted || (e1 !== null && e1 === e0)) say('That microphone sends no sound, so she can’t hear you. Pick another one, or Default.');
}
// The call ended up on the Bluetooth headphones' own mic (before the browser named the devices, or
// headphones put on during a call): move it to the MacBook's own mic, and bounce the sound in the HQ app.
async function keepHeadphones(app) {
  if (rt.btFixing || !IS_MAC || IS_PHONE || !rt.stream || app.state.cs === 'idle' || (pick('hq-mic') || {}).id) return;
  const t = rt.stream.getAudioTracks()[0], own = ownMic();
  if (!t || !own || !BT.test(t.label || '') || OWN_MIC.test(t.label || '')) return;
  rt.btFixing = true;
  try {
    for (let i = 0; i < 60 && app.state.cs === 'connecting'; i++) await sleep(250);
    if (!rt.pc || app.state.cs !== 'live') return;
    await switchMic(app);
    const now = rt.stream && rt.stream.getAudioTracks()[0];
    if (now && !BT.test(now.label || '')) { try { window.webkit.messageHandlers.hqAudio.postMessage({ do: 'bounce' }); } catch (e) { /* not the HQ app */ } }
  } catch (e) { /* stays as it is */ } finally { rt.btFixing = false; }
}
// The call's Microphone and sound sheet: pick the mic and (on a computer) the speaker, other sound on the
// Mac, and once, the device names (a browser names them only after a mic was allowed).
function soundSheet(app, st) {
  const rows = [];
  const save = (key, d) => {
    if (d) ls.set(key, JSON.stringify({ id: d.deviceId, label: d.label || '' })); else { try { localStorage.removeItem(key); } catch (e) { /* none */ } }
    app.setState({ [key === 'hq-mic' ? 'mic' : 'out']: d ? d.deviceId : '' });
  };
  const add = (list, key, word, kind) => {
    const p = pick(key), hit = devFind(list, p);
    const use = (on) => word + (on ? ' · in use' : '');
    rows.push({ a: 'Default', b: use(!hit && !(p && p.id)), pick: () => { save(key, null); if (kind === 'mic') switchMic(app); else applySink(); } });
    list.forEach((d, i) => rows.push({ a: d.label || word + ' ' + (i + 1), b: use(!!hit && hit.deviceId === d.deviceId),
      pick: () => { save(key, d); if (kind === 'mic') switchMic(app); else applySink(); } }));
  };
  const ins = devOf('audioinput'), outs = devOf('audiooutput');
  const can = typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.enumerateDevices;
  if (!can) rows.push({ a: 'This browser can’t choose one', b: 'The call uses the default microphone', pick: () => {} });
  else {
    add(ins, 'hq-mic', 'Microphone', 'mic');
    if (!IS_PHONE && CAN_SINK && outs.length) add(outs, 'hq-out', 'Her voice', 'out');
    else rows.push({ a: IS_IOS ? 'Where her voice plays' : 'Her voice', b: IS_PHONE ? (IS_IOS ? 'The iPhone decides: change it in Control Center' : 'It follows the microphone')
      : 'This browser can’t choose: it plays where the computer’s own sound goes', pick: () => {} });
    if (IS_MAC && !IS_PHONE) {
      const k = keepSound();
      rows.push({ a: 'Other sound: ' + (k ? 'Normal' : 'Lower'),
        b: !k ? 'Music and videos turn down while you’re on a call. Tap for normal'
          : onSpeakers() ? 'Stays normal with headphones on; through the MacBook’s speakers it still turns down. Tap to lower'
            : 'Music and videos stay at their normal volume. Tap to lower',
        pick: () => { ls.set('hq-keep-sound', k ? 'off' : 'on'); app.setState((x) => ({ keepSound: !k, cDev: (x.cDev || 0) + 1 })); switchMic(app); } });
    }
    if (!ins.some((d) => d.label) && navigator.mediaDevices.getUserMedia) {
      rows.push({ a: 'Show device names', b: 'HQ asks once, so each one shows its name', pick: async () => {
        try { const s = await navigator.mediaDevices.getUserMedia({ audio: true }); s.getTracks().forEach((t) => t.stop()); } catch (e) { /* not allowed */ }
        listDevices(app);
      } });
    }
  }
  return { title: IS_PHONE ? 'Microphone and sound' : 'Microphone and sound on this call', rows };
}
function micOpen(on) { if (rt.stream) rt.stream.getAudioTracks().forEach((t) => { t.enabled = on; }); }
// The moment a hold turns into talking: a short buzz (Android's vibrate; on an iPhone from iOS 18 a hidden
// switch flipped, which ticks; before that a soft click), and a short low sound so he hears it without looking.
// The mic sends silence while that sound plays, so it isn't heard as his words. Both silent with her voice off.
function oldIos() { const m = navigator.userAgent.match(/(?:iPhone|iPad|iPod).* OS (\d+)_/); return !!m && +m[1] < 18; }
function beep(type, f0, f1, peak, len) {
  const c = rt.audioCtx; if (!c) return;
  if (c.state === 'suspended') { try { c.resume(); } catch (e) { /* later */ } }
  const t = c.currentTime, o = c.createOscillator(), g = c.createGain();
  o.type = type; o.frequency.setValueAtTime(f0, t); if (f1) o.frequency.exponentialRampToValueAtTime(f1, t + len * 0.8);
  g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(peak, t + 0.006); g.gain.exponentialRampToValueAtTime(0.0001, t + len);
  o.connect(g).connect(c.destination); o.start(t); o.stop(t + len + 0.02);
}
function buzz(voiceOn) {
  try { if (navigator.vibrate && navigator.vibrate(25)) return; } catch (e) { /* none */ }
  if (oldIos()) { if (voiceOn) beep('sine', 1500, 0, 0.12, 0.04); return; }
  try {
    const label = document.createElement('label'), input = document.createElement('input');
    label.setAttribute('aria-hidden', 'true'); label.style.display = 'none';
    input.type = 'checkbox'; input.setAttribute('switch', '');
    label.appendChild(input); document.head.appendChild(label);
    label.click(); label.remove();
  } catch (e) { /* no tick */ }
}
const TALK_SOUND_MS = 180;
function talkSound(app) {
  if (!rt.audioCtx || !app.state.voiceOn) return;
  beep('triangle', 330, 210, 0.22, 0.13);
  micOpen(false);
  clearTimeout(rt.talkGate);
  rt.talkGate = setTimeout(() => { rt.talkGate = null; if (rt.holding) micOpen(true); }, TALK_SOUND_MS);
}
// Where the phone is, for travel advice, as the old page sends it: only when he allows his location in the
// app (Settings' weather place: hq-wx-gps), else only when the browser already allows it and he didn't pick his
// home place. When a call starts, when the page shows again, and every ten minutes while it shows.
let hereAt = 0;
async function sendHere(app, force) {
  if (app.demoMode || typeof navigator === 'undefined' || !navigator.geolocation) return;
  if (!force && Date.now() - hereAt < 10 * 60 * 1000) return;
  const want = ls.get('hq-wx-gps');
  let ok = want === '1';
  if (want !== '0' && want !== '1') { try { ok = (await navigator.permissions.query({ name: 'geolocation' })).state === 'granted'; } catch (e) { ok = false; } }
  if (!ok) return;
  navigator.geolocation.getCurrentPosition((p) => {
    hereAt = Date.now();
    app.api.post('api/here', { lat: p.coords.latitude.toFixed(4), lon: p.coords.longitude.toFixed(4) }, 'here').catch(() => {});
  }, () => {}, { enableHighAccuracy: true, timeout: 15000, maximumAge: 2 * 60 * 1000 });
}
function send(obj) {
  try { if (rt.dc && rt.dc.readyState === 'open') { rt.dc.send(JSON.stringify(obj)); return true; } } catch (e) { /* closed */ }
  return false;
}
// The microphone chosen (hq-mic), else the default one; see micAudio.
async function openMic(app) {
  await listDevices(null);
  rt.micKey = ((pick('hq-mic') || {}).id || '') + '|' + keepSound();
  const want = micAudio(true);
  try { return await navigator.mediaDevices.getUserMedia({ audio: want }); } catch (e) {
    if (!want.deviceId || !/Overconstrained|NotFound|NotReadable/.test((e && e.name) || '')) throw e;
    app.say('The chosen microphone isn’t here, so the default one is used.');
    return navigator.mediaDevices.getUserMedia({ audio: micAudio(false) });
  }
}
function gathered(pc) {
  return new Promise((res) => {
    if (pc.iceGatheringState === 'complete') return res();
    const done = () => { if (pc.iceGatheringState === 'complete') { pc.removeEventListener('icegatheringstatechange', done); res(); } };
    pc.addEventListener('icegatheringstatechange', done);
    setTimeout(res, 3000);
  });
}
// The transcript follows the newest line, unless he scrolled up to read.
function scrollLogs() {
  requestAnimationFrame(() => requestAnimationFrame(() => document.querySelectorAll('[data-hq-call-log]').forEach((el) => {
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 160) el.scrollTop = el.scrollHeight;
  })));
}
// The typing box grows line by line up to about six lines, then scrolls inside. A phone (a touch
// screen) gets a new line on Enter and sends with Send; a computer sends on Enter, Shift+Enter is a new line.
const BOX_MAX = 150;
export const coarse = () => typeof matchMedia !== 'undefined' && matchMedia('(pointer: coarse)').matches;
export function fit(el) {
  if (!el || !el.style) return;
  el.style.height = 'auto';
  const h = Math.min(el.scrollHeight, BOX_MAX);
  el.style.height = h + 'px';
  el.style.overflowY = el.scrollHeight > BOX_MAX ? 'auto' : 'hidden';
}
export function fitRef(el) { if (el) requestAnimationFrame(() => fit(el)); }
export function fitBoxes() {
  if (typeof document === 'undefined') return;
  // after the render that cleared the box (a render comes on the next frame, or within 100 ms when hidden)
  const all = () => document.querySelectorAll('textarea[data-hq-grow]').forEach(fit);
  requestAnimationFrame(() => requestAnimationFrame(all));
  setTimeout(all, 150);
}
// Her voice: the one picked on this device (hq-voice-<id>), else hers from the server.
function voiceFor(id, agents) {
  return ls.get('hq-voice-' + id) || ls.get('hq-voice') || ((agents || {})[APP[id]] || {}).voice || '';
}

// Her lines come with **bold** and *italics* marks: the transcript draws them (rich); the ask card's
// one line shows them plain.
function plainText(s) {
  return String(s || '').replace(/\*\*(.+?)\*\*/g, '$1').replace(/(^|[\s(])\*([^*\s](?:[^*]*[^*\s])?)\*(?=[\s).,!?:;]|$)/g, '$1$2').replace(/^#{1,6}\s+/gm, '');
}

function closeRtc() {
  clearInterval(rt.ping); rt.ping = null;
  clearInterval(rt.secT); rt.secT = null;
  clearTimeout(rt.retryT); rt.retryT = null;
  clearTimeout(rt.linger); rt.linger = null;
  clearTimeout(rt.holdT); rt.holdT = null;
  if (rt.tickT) { clearInterval(rt.tickT); rt.tickT = null; }
  try { if (rt.dc) rt.dc.close(); } catch (e) { /* gone */ }
  try { if (rt.pc) { rt.pc.onconnectionstatechange = null; rt.pc.close(); } } catch (e) { /* gone */ }
  if (rt.stream) rt.stream.getTracks().forEach((t) => t.stop());
  try { if (rt.wake) rt.wake.release(); } catch (e) { /* gone */ }
  rt.pc = rt.dc = rt.stream = rt.wake = null;
  rt.holding = false; rt.pressId = null; rt.cancellable = false;
  if (rt.audio) rt.audio.srcObject = null;
}
// Off the call: back to where he was before it (the call and its transcript leave the back stack).
const leaveCall = (x) => {
  const stack = x.stack.filter((k) => k !== 'call' && k !== 'transcript');
  if (x.screen !== 'call' && x.screen !== 'transcript') return { stack };
  return { screen: stack.length ? stack.pop() : 'home', stack };
};
// When the call ends while he reads it (the transcript, the Mac's call screen with its lines, or the call
// screen when she or the line ended it), what was said stays readable: the call's record opens with
// Continue this call (it calls back and goes on). His own Hang up on the phone's call screen goes back.
function ended(app, words) {
  rt.turn++;
  const how = rt.endHow; rt.endHow = '';
  closeRtc();
  const st0 = app.state;
  const inline = app.device === 'mac' && st0.design !== 'thread';
  const reading = st0.screen === 'transcript' || (st0.screen === 'call' && (inline || how !== 'button' || rt.fromT));
  rt.fromT = false;
  const said = st0.cLines.some((l) => !l.old && (l.who === 'me' || l.who === 'hq'));
  const keep = !app.demoMode && st0.onCall && reading && said && how !== 'switch' && how !== 'callback';
  const record = keep ? { agent: st0.callAgent, lines: st0.cLines.filter((l) => l.who !== 'divider'), started: st0.cStarted, at: Date.now(), before: rt.lastSaved || '' } : null;
  app.setState((x) => Object.assign({ onCall: false, confirmHang: false, cs: 'idle', cHold: false, cTrans: false, cCancel: false, cCxAsk: false, cUntapped: false,
    cMsg: '', cAgain: false, cLineDown: false, cRing: null, demo: false, second: null, sheet: x.sheet === 'add' || x.sheet === 'callSound' ? null : x.sheet },
  record ? { cEnded: record, screen: 'callLog', txLog: '__live', space: record.agent, stack: x.stack.filter((k) => k !== 'call' && k !== 'transcript') } : leaveCall(x)));
  if (record && app.entered) app.entered('callLog');
  if (words) app.say(words);
  // the call is saved after its end (the after-call work): past calls read again, as the old page showed the last call
  if (!app.demoMode && app.entered) for (const ms of [3000, 20000]) setTimeout(() => app.entered('pastCalls'), ms);
}
// Hang up: the server first (so the after-call work starts at once), then close.
function hangup(app, words, how) {
  rt.endHow = how || 'agent';
  send({ type: 'hangup' });
  const mine = rt.turn;
  setTimeout(() => { if (rt.turn === mine) ended(app, words); }, 250);
}
// It didn't connect: the call screen stays, with why. A call line that doesn't answer is tried again by itself.
function failed(app, msg, lineDown) {
  rt.turn++;
  closeRtc();
  app.setState({ cs: 'failed', cMsg: lineDown ? '' : msg, cAgain: !lineDown, cLineDown: !!lineDown, cHold: false, cTrans: false, cCancel: false });
  if (lineDown) {
    const mine = rt.turn;
    rt.retryT = setTimeout(() => { if (rt.turn === mine && app.state.cs === 'failed' && app.state.onCall) connect(app); }, RETRY_MS);
  }
}

function setOrb(app, js) {
  if (!ORB[js] || js === 'connecting') js = 'listening';
  app.setState((x) => (x.cTrans && (js === 'thinking' || js === 'speaking' || js === 'listening') ? { orb: js, cTrans: false } : { orb: js }));
  // Take that back: his next turn hides it; back at "your turn" it goes after 20 seconds.
  if (app.state.cCancel) {
    if (js === 'hearing' || js === 'transcribing') hideCancel(app);
    else if (js === 'listening' && !rt.cancellable) { if (!rt.linger) rt.linger = setTimeout(() => hideCancel(app), CANCEL_LINGER_MS); }
    else if (rt.linger) { clearTimeout(rt.linger); rt.linger = null; }
  }
  thinking(js === 'thinking', app.state);
}
function hideCancel(app) {
  rt.cancellable = false; clearTimeout(rt.linger); rt.linger = null;
  if (app.state.cCancel || app.state.cCxAsk) app.setState({ cCancel: false, cCxAsk: false });
}
// Take that back: at once while she hasn't started answering (or within three seconds of his turn going
// out); later the call asks first, and the server makes it his turn again.
const CANCEL_ASK_MS = 3000;
function sendCancel(app) {
  if (!app.state.cCancel) return;
  const early = rt.cancellable;
  if (!send({ type: 'cancel' })) return;
  hideCancel(app);
  if (early) setOrb(app, 'listening');
  app.say('Taken back. She won’t act on your last line');
}
function onMessage(app, ev) {
  let m;
  try { m = JSON.parse(ev.data); } catch (e) { return; }
  if (!m || typeof m !== 'object') return;
  const live = app.state.cs !== 'idle';
  if (m.type === 'hq-state') setOrb(app, m.state);
  else if (m.type === 'hq-chat' && m.text) {
    const who = m.who === 'hq' || m.who === 'filler' ? m.who : 'me';
    app.setState((x) => ({ cLines: x.cLines.concat([{ who, text: String(m.text), agent: m.agent || '', cancelled: false, at: clock(Date.now()) }]) }));
    scrollLogs();
  } else if (m.type === 'hq-cancellable') {
    rt.cancellable = m.on === true && app.state.cs === 'live';
    if (rt.cancellable) { rt.cancelSince = Date.now(); clearTimeout(rt.linger); rt.linger = null; app.setState({ cCancel: true }); }
  } else if (m.type === 'hq-cancelled') {
    app.setState((x) => {
      const lines = x.cLines.slice();
      for (let i = lines.length - 1; i >= 0; i--) if (lines[i].who === 'me') { lines[i] = Object.assign({}, lines[i], { cancelled: true }); break; }
      return { cLines: lines };
    });
  } else if (m.type === 'hq-hangup' && live) hangup(app);
  else if (m.type === 'hq-switch' && live) switchTo(app, APP[m.agent], m.call);
  else if (m.type === 'hq-callback' && live) callMeBack(app, APP[m.agent], m.call);
  else if (m.type === 'hq-three-way' && Array.isArray(m.agents)) app.setState({ cPanel: m.agents.map((id) => APP[id]).filter(Boolean) });
}
// She put another agent on: this call ends as a hang-up does and the other one is called, continuing it.
function switchTo(app, id, name) {
  hangup(app, '', 'switch');
  if (!id) return;
  setTimeout(() => { if (app.state.cs === 'idle') app.startCall(id, name ? { continue: name, handover: true } : null); }, 700);
}
// "Hang up and call me back": as on the old page, the page loads itself again (fresh page code) and
// calls the same agent at once, continuing this call. Kept for the reload in this tab only.
function callMeBack(app, id, name) {
  hangup(app, '', 'callback');
  try { sessionStorage.setItem('hq-callback', JSON.stringify({ agent: id || app.state.callAgent, call: name || '', at: Date.now() })); } catch (e) { /* no storage */ }
  setTimeout(() => location.reload(), 900);
}
// A call started without a tap may not be allowed to play her voice: one tap anywhere lets her through.
function untapped(app) {
  app.setState({ cUntapped: true });
  const go = () => { startAudio(); if (rt.audio) rt.audio.play().then(() => app.setState({ cUntapped: false })).catch(() => {}); };
  document.addEventListener('pointerdown', go, { once: true, capture: true });
}

// The connection itself: the mic, the offer, her answer. Again on "Try again", and while the line is down.
async function connect(app) {
  const mine = ++rt.turn;
  const st = app.state, o = rt.opts || {};
  const D = st.data.call || {};
  const agent = SRV[st.callAgent];
  const plain = st.cFree;
  closeRtc();
  app.setState({ cs: 'connecting', orb: 'connecting', cMsg: '', cAgain: false, cLineDown: false });
  try {
    if (!window.isSecureContext || !navigator.mediaDevices) throw Object.assign(new Error('Open this page through the https address.'), { plain: true });
    const stream = await openMic(app);
    if (mine !== rt.turn) { stream.getTracks().forEach((t) => t.stop()); return; }
    rt.stream = stream;
    micOpen(!app.state.muted);
    const pc = new RTCPeerConnection({ iceServers: [] });
    rt.pc = pc;
    stream.getAudioTracks().forEach((t) => pc.addTrack(t, stream));
    const dc = pc.createDataChannel('chat', { ordered: true });
    rt.dc = dc;
    dc.onmessage = (ev) => { if (mine === rt.turn) onMessage(app, ev); };
    dc.onopen = () => { rt.ping = setInterval(() => { try { dc.send('ping: ' + Date.now()); } catch (e) { /* closed */ } }, 1000); };
    pc.ontrack = (ev) => {
      const a = audioEl();
      a.srcObject = ev.streams[0] || new MediaStream([ev.track]);
      applyVoice(app.state.voiceOn); applySink();
      a.play().catch(() => untapped(app));
    };
    pc.onconnectionstatechange = () => {
      if (mine !== rt.turn) return;
      if (pc.connectionState === 'connected' && app.state.cs !== 'live') {
        app.setState((x) => ({ cs: 'live', orb: x.orb === 'connecting' ? 'listening' : x.orb, cStarted: x.cStarted || Date.now(), cNow: Date.now() }));
        clearInterval(rt.secT); rt.secT = setInterval(() => app.setState({ cNow: Date.now() }), 1000);
        keepHeadphones(app);
      }
      if ((pc.connectionState === 'failed' || pc.connectionState === 'closed') && app.state.cs !== 'idle') ended(app, 'The call ended');
    };
    await pc.setLocalDescription(await pc.createOffer());
    await gathered(pc);
    if (mine !== rt.turn) return;
    const rd = { mode: ((D.agents || {})[st.callAgent] || {}).load || 'quick', agent, free: plain, voice: voiceFor(agent, D.agents),
      voices: { donna: voiceFor('donna', D.agents), pepper: voiceFor('pepper', D.agents), moneypenny: voiceFor('moneypenny', D.agents) } };
    if (o.demo != null) { rd.demo = true; rd.demo_topic = String(o.demo || ''); }
    if (!plain) {
      for (const k of ['about', 'about_todo', 'about_coaching', 'about_news', 'ring']) if (o[k]) rd[k] = String(o[k]);
      if (o.continue) { rd.continue = String(o.continue); if (o.handover) rd.handover = true; else if (o.callback) rd.callback = true; }
    }
    let r;
    try {
      r = await fetch('api/offer', { method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type, request_data: rd }) });
    } catch (e) { if (mine === rt.turn) failed(app, '', true); return; }
    if (mine !== rt.turn) return;
    if (!r.ok) { if (r.status >= 500) failed(app, '', true); else failed(app, 'The call line said no (' + r.status + '). Try again in a moment.'); return; }
    const answer = await r.json();
    if (mine !== rt.turn) return;
    await pc.setRemoteDescription({ sdp: answer.sdp, type: answer.type });
    try { rt.wake = await navigator.wakeLock.request('screen'); } catch (e) { /* not here */ }
  } catch (e) {
    if (mine !== rt.turn) return;
    const name = (e && e.name) || '';
    failed(app, name === 'NotAllowedError' ? 'The microphone is blocked. Allow it for this page in Settings, then try again.'
      : (name === 'NotFoundError' || name === 'OverconstrainedError') ? 'No microphone was found. Plug one in or pick one in Settings, then try again.'
        : (e && e.plain ? e.message : 'The call didn’t start: ' + String((e && e.message) || e)));
  }
}

// Hold-to-talk on the Mute button (and the space bar on the Mac): a short tap mutes or unmutes;
// held, the mic is open and the turn stays his until he lets go.
function pressStart(app, id) {
  if (app.state.cs !== 'live' || rt.pressId !== null) return;
  rt.pressId = id; rt.wasMuted = app.state.muted; rt.holding = false; rt.tapUsed = id !== 'space';
  startAudio();
  micOpen(true);
  rt.holdT = setTimeout(() => {
    rt.holdT = null; rt.holding = true; hideCancel(app);
    buzz(app.state.voiceOn);
    talkSound(app);
    app.setState({ muted: false, cHold: true, cTrans: false });
    send({ type: 'ptt', held: true });
  }, HOLD_MS);
}
function letGo(app, id) {
  if (rt.pressId === null || (id !== undefined && id !== rt.pressId)) return;
  rt.pressId = null;
  setTimeout(() => { rt.tapUsed = false; }, 400); // the click that follows a press is the press's
  const tap = rt.holdT !== null;
  clearTimeout(rt.holdT); rt.holdT = null;
  if (app.state.cs !== 'live') { rt.holding = false; return; }
  if (rt.holding) {
    rt.holding = false; clearTimeout(rt.talkGate); rt.talkGate = null; micOpen(false);
    app.setState({ muted: true, cHold: false, cTrans: true });
    send({ type: 'ptt', held: false });
    setTimeout(() => { if (app.state.cTrans) app.setState({ cTrans: false }); }, 8000);
  } else if (tap) setMuted(app, !rt.wasMuted);
}
function setMuted(app, m) { micOpen(!m); app.setState({ muted: m }); }
function hook(app) {
  if (rt.hooked || typeof window === 'undefined') return;
  rt.hooked = true;
  document.addEventListener('pointerup', (ev) => letGo(app, ev.pointerId));
  document.addEventListener('touchend', (ev) => { if (ev.touches.length === 0) letGo(app); });
  window.addEventListener('blur', () => letGo(app));
  const ours = (ev) => {
    if (ev.code !== 'Space' || ev.metaKey || ev.ctrlKey || ev.altKey) return false;
    const t = ev.target;
    return !(t && t.closest && t.closest('textarea, input, select, [contenteditable], [role=dialog]'));
  };
  window.addEventListener('keydown', (ev) => {
    if (app.device !== 'mac' || app.state.cs !== 'live' || !ours(ev)) return;
    ev.preventDefault(); ev.stopPropagation();
    if (!ev.repeat && rt.pressId === null) pressStart(app, 'space');
  }, true);
  window.addEventListener('keyup', (ev) => {
    if (ev.code !== 'Space' || rt.pressId !== 'space') return;
    ev.preventDefault(); ev.stopPropagation();
    letGo(app, 'space');
  }, true);
  // A mic or headphones plugged in or out: the list again, and the headphones kept in full sound.
  try { if (navigator.mediaDevices && navigator.mediaDevices.addEventListener) navigator.mediaDevices.addEventListener('devicechange', () => listDevices(app).then(() => keepHeadphones(app))); } catch (e) { /* none */ }
  // Closing the page counts as hanging up.
  window.addEventListener('pagehide', (ev) => { if (!ev.persisted) send({ type: 'hangup' }); });
  document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState === 'visible') sendHere(app, false);
    if (document.visibilityState === 'visible' && app.state.cs === 'live') { try { rt.wake = await navigator.wakeLock.request('screen'); } catch (e) { /* not here */ } }
  });
  setInterval(() => { if (!document.hidden) sendHere(app, false); }, 10 * 60 * 1000);
  sendHere(app, true);
}

// Installed on the app: start a call with an agent, from wherever you are.
export const methods = {
  startCall(a, about) {
    if (this.demoMode || typeof window === 'undefined') {
      this.setState((st) => ({
        onCall: true, callAgent: a, phase: 0, confirmHang: false, muted: false, yes: null, second: null, takenBack: false, incoming: false, demo: false,
        screen: 'call', stack: st.screen === 'call' ? st.stack : st.stack.concat([st.screen])
      }));
      return;
    }
    const id = APP[a] || 'donna';
    hook(this);
    const st = this.state;
    const D = st.data.call || {};
    const named = (k) => (D.names || NAMES)[k] || NAMES[k];
    if (st.onCall && st.cs !== 'idle') {
      // already on a call: open it (Add someone brings another one in)
      this.setState((x) => ({ screen: 'call', stack: x.screen === 'call' ? x.stack : x.stack.concat([x.screen]) }));
      if (id !== st.callAgent) this.say('You’re on a call with ' + named(st.callAgent) + '. Add someone brings ' + named(id) + ' in.');
      return;
    }
    const o = about && typeof about === 'object' ? about : {};
    const isDemo = o.demo != null;
    const plain = !!(st.free || D.freeOnly) || isDemo;
    rt.opts = o;
    startAudio(); // inside the tap, before anything waits
    this.setState((x) => ({
      onCall: true, callAgent: id, confirmHang: false, muted: false, incoming: false, demo: isDemo, second: null,
      cs: 'connecting', orb: 'connecting', cLines: [], cPanel: [], cStarted: 0, cNow: Date.now(), cMsg: '', cAgain: false, cLineDown: false,
      cCancel: false, cHold: false, cTrans: false, cUntapped: false, cAnswered: -1, cRing: null, cFree: plain, cLabel: '', cSeen: 0, cCxAsk: false,
      tour: isDemo ? -1 : x.tour,
      screen: 'call', stack: x.screen === 'call' ? x.stack : x.stack.concat([x.screen])
    }));
    const go = () => connect(this);
    if (!plain) sendHere(this, true);
    // the newest saved call before this one, so the record of this call is known once it's saved
    rt.lastSaved = null;
    this.api.get('api/last-call').then((d) => { if (rt.lastSaved === null) rt.lastSaved = (d && d.name) || ''; }).catch(() => {});
    if (o.continue && !plain) {
      // a continued call starts with the earlier call's lines, then a line where this one begins
      this.api.get('api/calls/' + encodeURIComponent(o.continue)).then((data) => {
        const lines = ((data && data.lines) || []).filter((l) => l.text && l.who !== 'filler')
          .map((l) => ({ who: l.who === 'hq' ? 'hq' : 'me', text: l.text, agent: l.agent || (data && data.agent) || '', cancelled: !!l.cancelled, old: true, at: l.at || l.time || '' }));
        const div = o.handover ? named(id) + ' picked up' : (o.callback ? 'Called you back' : 'Continued now');
        this.setState({ cLines: lines.concat([{ who: 'divider', text: div, agent: '', cancelled: false }]) });
      }).catch(() => {}).then(go);
    } else go();
  }
};

// The real data: the agents as the server has them (voice, load), and whether this line is Free only.
// The first time, also a call to make right away: after "call me back" (the reload) or a ring
// (?ring=N&agent=ID, from the "… is calling" notification).
export async function load(app) {
  hook(app);
  if (!rt.startedOnce) {
    rt.startedOnce = true;
    if (ls.get('hq-voice-off') === 'on') app.setState({ voiceOn: false });
    let back = null;
    try { back = JSON.parse(sessionStorage.getItem('hq-callback') || 'null'); sessionStorage.removeItem('hq-callback'); } catch (e) { /* no storage */ }
    const q = new URLSearchParams(location.search), ring = q.get('ring'), who = APP[q.get('agent') || ''] || 'donna';
    if (ring) {
      q.delete('ring'); q.delete('agent');
      try { history.replaceState(null, '', location.pathname + (q.toString() ? '?' + q : '')); } catch (e) { /* keep it */ }
      // She's calling: the ring screen, so his tap on Pick up is also the tap that lets her voice play.
      if (app.state.cs === 'idle') app.setState({ incoming: true, cRing: { n: ring, agent: who } });
    } else if (back && Date.now() - back.at < 90000 && app.state.cs === 'idle') {
      app.startCall(APP[back.agent] || 'donna', back.call ? { continue: back.call, callback: true } : null);
    }
  }
  const j = await app.api.get('api/agents');
  const agents = {}, names = Object.assign({}, NAMES);
  for (const a of (j && j.agents) || []) { const k = APP[a.id]; if (k) { agents[k] = a; names[k] = a.name; } }
  app.setData('call', { agents, names, freeOnly: !!(j && j.free_only) });
}

const toLines = (arr, ag) => arr.map((b) => (b[0] === 'm'
  ? { who: 'You', t: b[1], nc: '#15803d', fc: '#0f172a', fs: '16px', fw: '500' }
  : (b[0] === 'w' ? { who: ag.name, t: b[1], nc: ag.accent, fc: '#64748b', fs: '14px', fw: '400' } : { who: ag.name, t: b[1], nc: ag.accent, fc: '#0f172a', fs: '16px', fw: '400' })));

export function vals(st, ctx, D) {
  return ctx.app.demoMode || D === demo ? demoVals(st, ctx, D) : realVals(st, ctx, D || {});
}

// The prototypes' made-up call, unchanged (demo mode).
function demoVals(st, ctx, D) {
  const { app, AG, sc } = ctx;
  const say = (t) => app.say(t);
  const ca = AG[st.callAgent];
  const showMini = st.onCall && sc !== 'call' && sc !== 'transcript';
  const call = {
    donna: () => app.startCall('donna'), pepper: () => app.startCall('pepper'), mp: () => app.startCall('mp'),
    space: () => app.startCall(st.space), chat: () => app.startCall(st.chatAgent), textTo: () => app.startCall(st.textTo)
  };
  // What was said on the call (the live transcript)
  let tLines = toLines(D.callLines[st.callAgent], ca);
  if (st.callAgent === D.askOf && st.yes) tLines = tLines.concat(toLines(D.answers[st.yes], ca));
  const sec = st.second ? AG[st.second] : null;
  const tl2 = tLines.map((l) => Object.assign({ deco: 'none' }, l));
  if (st.takenBack) { for (let i = tl2.length - 1; i >= 0; i--) { if (tl2[i].who === 'You') { tl2[i] = Object.assign({}, tl2[i], { deco: 'line-through', fc: '#94a3b8' }); break; } } }
  if (sec) tl2.push({ who: sec.name, t: sec.name + ' picked up and is listening in.', nc: sec.accent, fc: sec.accent, fs: '14px', fw: '600', deco: 'none' });
  const sheets = {
    add: { title: 'Bring someone into the call', rows: ORDER.filter((k) => k !== st.callAgent).map((k) => ({ a: AG[k].name, b: AG[k].role, pick: () => { app.setState({ second: k, sheet: null }); say(AG[k].name + ' picked up'); } })) }
  };
  const mac = ctx.device === 'mac';
  return {
    sheets,
    values: {
      call, chat: { call: () => app.go('transcript') }, ca, phase: PHASES[st.phase], ring: RINGS[st.phase],
      showMini, padCls: showMini ? 'pt' : '', chatTop: showMini ? '12px' : '52px',
      cyclePhase: () => app.setState((x) => ({ phase: (x.phase + 1) % 5 })),
      toggleMute: () => app.setState((x) => ({ muted: !x.muted })), muteLabel: st.muted ? 'Muted: she can’t hear you' : 'Mute',
      muteBg: st.muted ? '#fef3c7' : '#ffffff', muteFg: st.muted ? '#78350f' : '#0f172a', muteShort: st.muted ? 'Muted' : 'Mute',
      askHang: () => app.setState({ confirmHang: true }), stayOn: () => app.setState({ confirmHang: false }),
      hangUp: () => app.setState((x) => { const stack = x.stack.slice(); const prev = stack.length ? stack.pop() : 'home'; return { onCall: false, confirmHang: false, screen: prev, stack }; }),
      hangFromT: () => app.setState((x) => { const stack = x.stack.slice(); stack.pop(); return { screen: 'call', stack, confirmHang: true }; }),
      confirmHang: st.confirmHang,
      tLines: tl2, askOpen: st.callAgent === D.askOf && !st.yes,
      sayYes: () => app.setState({ yes: 'yes' }), sayNo: () => app.setState({ yes: 'no' }),
      callBg: sec ? 'linear-gradient(135deg, ' + ca.tint + ' 50%, ' + sec.tint + ' 50%)' : ca.tint,
      callTitle: sec ? ca.name + ' and ' + sec.name : ca.name, hasSecond: !!sec, sec: sec || ca,
      takeBack: () => { app.setState({ takenBack: true }); say('Taken back. She won’t act on your last line'); },
      callMeBack: () => { app.setState({ phase: 0 }); say(ca.name + ' hangs up and calls you straight back'); },
      toggleVoice: () => app.setState((x) => ({ voiceOn: !x.voiceOn })), voiceLabel: st.voiceOn ? 'Voice off' : 'Voice on',
      sheetAdd: () => app.setState({ sheet: 'add' }),
      demoOn: st.demo && sc === 'call', callErr: st.offline && sc === 'call',
      demoCall: { donna: () => { app.startCall('donna'); app.setState({ demo: true, tour: -1 }); }, pepper: () => { app.startCall('pepper'); app.setState({ demo: true }); } },
      incoming: st.incoming, pickUp: () => { app.setState({ incoming: false }); app.startCall('donna'); }, decline: () => { app.setState({ incoming: false }); say('Donna will text you instead'); },
      // what the templates gained for the real call, with the design's own words here
      cl: { elapsed: '00:42', started: '14:19', ask: 'shall I move the gym to 20:00?', retry: () => app.setState({ offline: false }), aboutAppt: () => app.startCall('donna'), aboutTodo: () => app.startCall('donna'),
        msgOn: false, msg: '', againOn: false, again: () => {}, press: () => {}, noMenu: () => {}, send: () => {},
        typed: (e) => { app.keepDraft('callTyped', e.target); fit(e.target); }, key: () => {}, grow: fitRef, enterHint: 'send',
        newOn: false, newN: '', cxAsk: false, cxKeep: () => {}, cxYes: () => {}, sound: () => say('Pick the microphone in Settings, Microphone and sound'),
        orbHint: mac ? '. Click to see the next state' : '. Tap to see the next state',
        hint: mac ? 'Space bar: tap to mute, hold to talk' : 'Hold Mute to talk · tap the circle to see her states' }
    }
  };
}

// The last call on home: the newest saved call with any agent (the texts area reads /api/calls), opening
// its record with Continue this call. Only when there is one and no call is on.
function lastCall(app, st, AG) {
  const calls = ((st.data || {}).texts || {}).calls;
  const c = calls && calls[0];
  if (!c || st.onCall || st.cs !== 'idle') return { on: false, line: '', go: () => {}, color: '#64748b' };
  const k = ORDER.find((x) => AG[x] && AG[x].name === c.agent) || 'donna';
  const today = new Date(), yday = new Date(today); yday.setDate(today.getDate() - 1);
  const iso = (d) => d.getFullYear() + '-' + two(d.getMonth() + 1) + '-' + two(d.getDate());
  const day = c.date === iso(today) ? 'today' : c.date === iso(yday) ? 'yesterday' : String(c.started || c.date).split(',')[0];
  return { on: true, line: 'Last call with ' + AG[k].name + ' · ' + day + (c.time ? ' ' + c.time : ''), color: AG[k].accent,
    go: () => app.go('callLog', { txLog: c.name, space: k }) };
}

// The real call.
function realVals(st, ctx, D) {
  const { app, AG, sc } = ctx;
  const say = (t) => app.say(t);
  // Her card on the call: her area's line, else what she's for (as the old page shows before a call).
  const base = AG[st.callAgent] || AG.donna;
  const ca = base.line ? base : Object.assign({}, base, { line: ((D.agents || {})[st.callAgent] || {}).speciality || base.role });
  const live = st.cs === 'live';
  const showMini = st.onCall && sc !== 'call' && sc !== 'transcript';
  const start = (k, o) => () => app.startCall(k, o);
  const call = {
    donna: start('donna'), pepper: start('pepper'), mp: start('mp'),
    space: () => app.startCall(st.space), chat: () => app.startCall(st.chatAgent), textTo: () => app.startCall(st.textTo)
  };
  // Who's on it: a three-way call has two, a four-way three (the server says who).
  const panel = st.cPanel.length > 1 ? st.cPanel : [];
  const others = panel.filter((k) => k !== st.callAgent && AG[k]);
  const secKey = others[0] || null;
  const sec = secKey ? AG[secKey] : null;
  const ter = others[1] ? AG[others[1]] : null;
  const tint = (a) => (a && a.tint) || '#ffffff';
  const byName = (n) => ORDER.map((k) => AG[k]).find((a) => a.name === n);
  // What was said on the call
  const tLines = st.cLines.map((l) => {
    if (l.who === 'divider') return { who: '', t: l.text, nc: '#94a3b8', fc: '#94a3b8', fs: '13px', fw: '600', deco: 'none' };
    if (l.who === 'me') return { who: 'You', t: rich(l.text, { marks: false }), nc: '#15803d', fc: l.cancelled ? '#94a3b8' : '#0f172a', fs: '16px', fw: '500', deco: l.cancelled ? 'line-through' : 'none' };
    const her = byName(l.agent) || ca;
    return { who: her.name, t: rich(l.text, { marks: l.who !== 'filler' }), nc: her.accent, fc: l.who === 'filler' ? '#64748b' : '#0f172a', fs: l.who === 'filler' ? '14px' : '16px', fw: '400', deco: 'none' };
  });
  // The lines that came in while what was said wasn't in view: a count on its button and the mini bar.
  const mac = ctx.device === 'mac';
  const tView = sc === 'transcript' || (sc === 'call' && mac && st.design !== 'thread');
  if (tView && st.cSeen !== st.cLines.length) app.quietState({ cSeen: st.cLines.length });
  const newN = tView ? 0 : st.cLines.slice(st.cSeen || 0).filter((l) => !l.old && (l.who === 'me' || l.who === 'hq')).length;
  // A choice made in Settings' Sound screen during the call takes over at once, as one made here.
  if (live && typeof window !== 'undefined') {
    if (((pick('hq-mic') || {}).id || '') + '|' + keepSound() !== rt.micKey) { rt.micKey = ((pick('hq-mic') || {}).id || '') + '|' + keepSound(); setTimeout(() => switchMic(app), 0); }
    if (((pick('hq-out') || {}).id || '') !== rt.outKey) setTimeout(applySink, 0);
  }
  // She asks something: her last line is a question and it's his turn. Yes or No goes in as his typed answer.
  let ask = null, askAt = -1;
  for (let i = st.cLines.length - 1; i >= 0; i--) {
    const l = st.cLines[i];
    if (l.who === 'me' || l.who === 'divider') break;
    if (l.who === 'hq') { if (/\?\s*$/.test(l.text) && !l.old) { ask = l; askAt = i; } break; }
  }
  const askOpen = live && !!ask && st.orb === 'listening' && st.cAnswered !== askAt;
  const typedNow = (text) => {
    if (!text) return false;
    if (st.cs !== 'live') { say('The call isn’t connected yet'); return false; }
    if (text.length > TYPED_MAX) { say('That’s ' + text.length + ' characters; one message takes ' + TYPED_MAX + '. Send it in two parts.'); return false; }
    if (!send({ type: 'typed', text })) { say('Couldn’t send that. Try again.'); return false; }
    hideCancel(app);
    return true;
  };
  const answer = (w) => () => { if (typedNow(w)) app.setState({ cAnswered: askAt }); };
  const sheets = {
    callSound: soundSheet(app, st),
    add: { title: 'Bring someone into the call', rows: ORDER.filter((k) => k !== st.callAgent && !others.includes(k)).map((k) => ({ a: AG[k].name, b: AG[k].role,
      pick: () => { app.setState({ sheet: null }); if (typedNow('Bring ' + AG[k].name + ' into the call, please.')) say('Asked ' + ca.name + ' to bring ' + AG[k].name + ' in'); } }))
      .concat(ORDER.every((k) => k === st.callAgent || others.includes(k)) ? [{ a: 'Everyone’s on the call', b: '', pick: () => app.setState({ sheet: null }) }] : []) }
  };
  const [label, ring] = st.cs === 'failed' ? ['Not connected', 4] : (ORB[st.cs === 'connecting' ? 'connecting' : st.orb] || ORB.listening);
  const phase = live && st.muted && !st.cHold ? 'Muted' : (live && st.orb === 'speaking' && !st.voiceOn ? 'Speaking · voice off' : label);
  const secs = live && st.cStarted ? Math.max(0, Math.floor((st.cNow - st.cStarted) / 1000)) : 0;
  const elapsed = live ? two(Math.floor(secs / 60)) + ':' + two(secs % 60) : (st.cs === 'failed' ? 'not connected' : 'calling…');
  const hint = st.cHold ? 'Let go when you’re done' : st.cTrans ? 'Turning your last words into text…'
    : (live && st.muted) ? (mac ? 'Muted · hold the space bar to talk' : 'Muted · hold the button to talk')
      : (mac ? 'Space bar: tap to mute, hold to talk' : 'Hold Mute to talk');
  const muteOn = st.muted && !st.cHold;
  const msg = st.cUntapped ? 'Tap anywhere to hear her.' : st.cMsg;
  const hangNow = () => { app.setState({ confirmHang: false }); if (st.cs === 'live' || st.cs === 'connecting') hangup(app, '', 'button'); else ended(app); };
  const sendBox = () => {
    const t = ((app.state.drafts || {}).callTyped || '').trim();
    if (typedNow(t)) { app.setState((x) => ({ drafts: Object.assign({}, x.drafts, { callTyped: '' }) })); fitBoxes(); }
  };
  return {
    sheets,
    submit: { callTyped: (t) => { if (!typedNow(t)) app.setState((x) => ({ drafts: Object.assign({}, x.drafts, { callTyped: t }) })); } },
    values: {
      call, chat: { call: () => app.go('transcript') }, ca, ring, callLast: lastCall(app, st, AG),
      phase,
      showMini, padCls: showMini ? 'pt' : '', chatTop: showMini ? '12px' : '52px',
      // The circle: a tap lets her voice through when the browser held it back; else nothing.
      cyclePhase: () => { startAudio(); if (rt.audio && st.cUntapped) rt.audio.play().then(() => app.setState({ cUntapped: false })).catch(() => {}); },
      // A pointer press is handled by its hold (pressStart, letGo); a keyboard press toggles here.
      toggleMute: () => { if (rt.tapUsed) { rt.tapUsed = false; return; } if (st.cs === 'live') setMuted(app, !st.muted); },
      muteLabel: st.cHold ? 'Talking…' : st.cTrans ? 'Transcribing…' : (muteOn ? 'Muted: she can’t hear you' : 'Mute'),
      muteBg: st.cHold ? '#dcfce7' : st.cTrans ? '#fef9c3' : (muteOn ? '#fef3c7' : '#ffffff'),
      muteFg: st.cHold ? '#14532d' : (muteOn || st.cTrans ? '#78350f' : '#0f172a'),
      muteShort: st.cHold ? 'Talking…' : st.cTrans ? 'Transcribing…' : (muteOn ? 'Muted' : 'Mute'),
      askHang: () => { rt.fromT = false; app.setState({ confirmHang: true }); }, stayOn: () => app.setState({ confirmHang: false }),
      hangUp: hangNow,
      hangFromT: () => { rt.fromT = true; app.setState((x) => { const stack = x.stack.slice(); if (stack[stack.length - 1] === 'call') stack.pop(); return { screen: 'call', stack, confirmHang: true }; }); },
      confirmHang: st.confirmHang,
      tLines, askOpen,
      sayYes: answer('Yes'), sayNo: answer('No'),
      callBg: ter ? 'linear-gradient(135deg, ' + tint(ca) + ' 33.3%, ' + tint(sec) + ' 33.3% 66.6%, ' + tint(ter) + ' 66.6%)'
        : sec ? 'linear-gradient(135deg, ' + ca.tint + ' 50%, ' + sec.tint + ' 50%)' : ca.tint,
      // with three on the line the title names them all
      callTitle: ter ? ca.name + ', ' + sec.name + ' and ' + ter.name : sec ? ca.name + ' and ' + sec.name : ca.name, hasSecond: !!sec && !ter, sec: sec || ca,
      takeBack: () => {
        if (!st.cCancel) { say('Nothing to take back right now'); return; }
        if (!rt.cancellable || Date.now() - rt.cancelSince > CANCEL_ASK_MS) { app.setState({ cCxAsk: true }); return; }
        sendCancel(app);
      },
      callMeBack: () => { if (typedNow('Hang up and call me back, please.')) say('Asked ' + ca.name + ' to call you straight back'); },
      toggleVoice: () => { const on = !st.voiceOn; ls.set('hq-voice-off', on ? 'off' : 'on'); applyVoice(on); app.setState({ voiceOn: on }); thinking(st.orb === 'thinking', Object.assign({}, st, { voiceOn: on })); },
      voiceLabel: st.voiceOn ? 'Voice off' : 'Voice on',
      sheetAdd: () => { if (st.cs !== 'live') { say('The call isn’t connected yet'); return; } app.setState({ sheet: 'add' }); },
      demoOn: st.demo && st.onCall && sc === 'call', callErr: (st.offline || st.cLineDown) && sc === 'call',
      demoCall: { donna: start('donna', { demo: '' }), pepper: start('pepper', { demo: '' }), mp: start('mp', { demo: '' }) },
      incoming: st.incoming,
      pickUp: () => { const r = st.cRing; app.setState({ incoming: false, cRing: null }); app.startCall(r ? r.agent : 'donna', r ? { ring: r.n } : null); },
      decline: () => { const r = st.cRing; app.setState({ incoming: false, cRing: null }); say(((r && AG[r.agent]) || AG.donna).name + ' will text you instead'); },
      cl: {
        // Call Donna about this: the open appointment, the open to-do item (their ids go with the call)
        aboutAppt: () => app.startCall('donna', st.apptId ? { about: String(st.apptId) } : null),
        aboutTodo: () => app.startCall('donna', st.tdItem ? { about_todo: String(st.tdItem) } : null),
        elapsed, started: st.cStarted ? clock(st.cStarted) : 'just now', ask: ask ? plainText(ask.text) : '',
        retry: () => { if (st.cLineDown) connect(app); else app.api.get('api/busy').catch(() => {}); },
        msgOn: !!msg, msg, againOn: st.cAgain && st.cs === 'failed', again: () => connect(app),
        press: (e) => {
          if (st.cs !== 'live') { rt.tapUsed = false; return; }
          if (e && e.preventDefault) e.preventDefault();
          try { e.currentTarget.setPointerCapture(e.pointerId); } catch (x) { /* fine without */ }
          pressStart(app, e && e.pointerId != null ? e.pointerId : 'p');
        },
        noMenu: (e) => { if (e && e.preventDefault) e.preventDefault(); },
        send: sendBox,
        // the typing box: it grows with what's typed; Enter sends on a computer, a new line on a phone
        typed: (e) => { app.keepDraft('callTyped', e.target); fit(e.target); },
        key: (e) => { if (e.key !== 'Enter' || e.shiftKey || e.isComposing || coarse()) return; e.preventDefault(); sendBox(); },
        grow: fitRef, enterHint: coarse() ? 'enter' : 'send',
        // lines said while what was said wasn't in view
        newOn: newN > 0, newN: newN > 9 ? '9+' : String(newN),
        // the same count on the mini bar while the call isn't in view
        unread: showMini && newN ? (newN > 9 ? '9+' : String(newN)) : '',
        // Take that back when she's well into answering: asked first
        cxAsk: st.cCxAsk && live, cxKeep: () => app.setState({ cCxAsk: false }), cxYes: () => { app.setState({ cCxAsk: false }); sendCancel(app); },
        // the microphone and where her voice plays, during the call
        sound: () => { listDevices(app); app.setState({ sheet: 'callSound' }); },
        orbHint: st.cUntapped ? '. Tap to hear her' : '', hint
      }
    }
  };
}
