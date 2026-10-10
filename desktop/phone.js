// H28: the phone version of the Mac app. 10 October 2026 (call at 14:33): "after we designed the desktop
// version, then we can just make like a phone version. That looks similar like it. ... And we can still do
// the localhost thing and just drop it for both. Desktop and... The phone, that doesn't matter."
//
// The status server serves desktop/shell.html (the Mac app's own strip, unchanged) at /hq, with this script
// in its <head> and phone.css. This script stands in for the Mac app (HQ.swift): it answers the strip's
// messages (ready, tab, fix, height), asks the status server every 5 seconds how things are (/hq.json, the
// same hq_control.py health the Mac app runs), and puts the status page and the call page under the strip.
// On the phone (the tailnet address, port 8444) the call page is the call line's own address on the same
// host, port 8443; on this MacBook it is 127.0.0.1:7860, as in the Mac app. [Claude's choices: the same strip
// file as the Mac app, so both always look the same; the call page loads only when Call is opened.]
(() => {
  const EVERY = 5000;
  const callURL = () => (location.port === '8444'
    ? `https://${location.hostname}:8443/`
    : 'http://127.0.0.1:7860/') + '?app=1';  // H46: it has the Status tab, so the call page leaves out its own
  let frames = null;
  let timer = null;

  const strip = () => window.hq;
  async function health() {
    try {
      const r = await fetch('/hq.json', { cache: 'no-store' });
      if (!r.ok) throw new Error(String(r.status));
      strip()?.update(await r.json());
    } catch {
      strip()?.update({ light: 'down', mood: 'sleep', headline: 'The Mac doesn’t answer', off: [], routines: [] });
    }
  }
  function build() {
    if (frames) return;
    const main = document.createElement('main');
    main.id = 'frames';
    const mk = (id, src, allow) => {
      const f = document.createElement('iframe');
      f.id = id;
      f.title = id === 'frame-status' ? 'Status' : 'Call';
      if (allow) f.allow = allow;
      if (src) f.src = src;
      main.append(f);
      return f;
    };
    frames = {
      status: mk('frame-status', '/'),
      call: mk('frame-call', '', 'microphone; autoplay; clipboard-write'),
    };
    document.body.append(main);
    tab(localStorage.getItem('hq-tab') === 'call' ? 'call' : 'status');
  }
  function tab(t) {
    if (!frames) return;
    if (t === 'call' && !frames.call.getAttribute('src')) frames.call.src = callURL();
    frames.status.hidden = t !== 'status';
    frames.call.hidden = t !== 'call';
    document.body.dataset.tab = t;
    strip()?.tab(t);
    try { localStorage.setItem('hq-tab', t); } catch {}
  }
  async function fix() {
    let said = 'Nothing was off';
    try {
      const r = await fetch('/hq/fix', { method: 'POST', headers: { 'x-hq': 'fix' } });
      const out = await r.json();
      const ok = (out.fixed || []).filter((f) => f.ok).map((f) => f.what);
      const bad = (out.fixed || []).filter((f) => !f.ok).map((f) => f.what);
      said = ok.length ? ok.join(', ') : said;
      if (bad.length) said += (ok.length ? '; ' : '') + 'couldn’t do: ' + bad.join(', ');
    } catch {
      said = 'The Mac doesn’t answer';
    }
    setTimeout(() => { strip()?.fixing(false, said); health(); }, 1500);
  }
  function onMessage(m) {
    if (m.do === 'ready') {
      build();
      health();
      clearInterval(timer);
      timer = setInterval(health, EVERY);
    } else if (m.do === 'tab') tab(m.tab);
    else if (m.do === 'fix') fix();
    // 'height' is the Mac window's business; on the phone the panel simply pushes the pages down.
  }
  // The strip talks through webkit.messageHandlers.hq, as in the Mac app.
  const shim = { messageHandlers: { hq: { postMessage: onMessage } } };
  try {
    Object.defineProperty(window, 'webkit', { value: shim, configurable: true, writable: true });
  } catch {
    window.webkit = shim;
  }
  window.hqPhone = { tab, health, callURL, frames: () => frames };
  document.addEventListener('visibilitychange', () => { if (!document.hidden) health(); });
})();
