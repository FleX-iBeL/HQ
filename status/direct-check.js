// F102: what this phone sees of her texts, looked at once on every open and told to the status server, so a push that
// Apple accepts and the phone never shows isn't a guess again. Used by her chat (status/direct.html, also in the sheet
// over the call page, which is how the phone opens it) and by the call page itself (the home-screen app's own page, so
// the list stays current even when her chat isn't opened). It keeps the phone on the list: a subscription that's there
// is sent again, a missing one is made when notifications are allowed. No step can hang: each has a time limit and its
// error goes in the report. Nothing here can fail or slow the chat: check() never throws and the report isn't waited on.
(() => {
  const LIMIT = 6000;
  const said = (e) => String((e && e.name ? e.name + ': ' : '') + ((e && e.message) || e || '')).slice(0, 160);
  const b64 = (s) => Uint8Array.from(atob(s.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - s.length % 4) % 4)), (c) => c.charCodeAt(0));
  const timed = (p) => {
    let t;
    const late = new Promise((_, no) => { t = setTimeout(() => no(new Error(`no answer in ${LIMIT / 1000} seconds`)), LIMIT); });
    return Promise.race([p, late]).finally(() => clearTimeout(t));
  };
  // One step: its answer, or undefined with its error kept under its name.
  const step = async (r, name, f) => {
    try { return await timed(f()); } catch (e) { r.errors[name] = said(e); return undefined; }
  };
  const post = (path, body) => fetch(path, { method: 'POST', headers: { 'x-hq': 'direct', 'content-type': 'application/json' },
    body: JSON.stringify(body) });
  const sameKey = (sub, key) => {
    try {
      const raw = sub.options && sub.options.applicationServerKey;
      if (!raw) return null;
      const a = new Uint8Array(raw), b = b64(key);
      return a.length === b.length && a.every((x, i) => x === b[i]);
    } catch { return null; }  // this phone doesn't say which key it was made with
  };
  const worker = (r, reg) => {
    r.registered = !!reg;
    if (!reg) return;
    r.scope = reg.scope || '';
    r.active = reg.active ? reg.active.state || 'active' : '';
    r.waiting = !!(reg.waiting || reg.installing);
  };
  async function look(r, tap) {
    if (!('serviceWorker' in navigator) || !('PushManager' in window) || !('Notification' in window)) {
      r.problem = 'nosupport';
      return;
    }
    r.permission = Notification.permission;
    r.controlled = !!navigator.serviceWorker.controller;
    worker(r, await step(r, 'registration', () => navigator.serviceWorker.getRegistration('/')));
    if (r.permission !== 'granted') { r.problem = r.permission; return; }
    const reg = await step(r, 'register', () => navigator.serviceWorker.register('/direct-sw.js', { scope: '/' }));
    if (!reg) { r.problem = 'sw'; return; }
    const ready = await step(r, 'ready', () => navigator.serviceWorker.ready);
    worker(r, ready || reg);
    if (!ready) { r.problem = 'sw'; return; }
    const k = await step(r, 'key', async () => (await fetch('/direct/key', { cache: 'no-store' })).json());
    const key = k && k.key;
    let sub = await step(r, 'subscription', () => ready.pushManager.getSubscription());
    if (sub) {
      r.subscription = String(sub.endpoint).slice(-14);
      r.keyMatch = key ? sameKey(sub, key) : null;
      // Only on his tap: a page that read a wrong key must never throw a good subscription away by itself.
      if (tap && key && r.keyMatch === false) {
        await step(r, 'unsubscribe', () => sub.unsubscribe());
        sub = null;
      }
    }
    if (!sub) {
      if (!key) { r.problem = 'key'; return; }
      sub = await step(r, 'subscribe', () => ready.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64(key) }));
      if (!sub) { r.problem = 'nosub'; return; }  // Safari can ask for a tap for this: the page offers one
      r.made = true;
      r.subscription = String(sub.endpoint).slice(-14);
      r.keyMatch = true;
    }
    const sent = await step(r, 'post', () => post('/direct/subscribe', { subscription: sub.toJSON(), device: navigator.userAgent }));
    r.posted = !!(sent && sent.ok);
    if (sent && !sent.ok) r.errors.post = `HTTP ${sent.status}`;
    if (r.keyMatch === false) r.problem = 'oldkey';
    else if (!r.posted) r.problem = 'post';
  }
  async function check({ tap = false } = {}) {
    const r = { kind: 'page', origin: '', page: '', frame: false, top: '', standalone: false, permission: 'none', registered: false,
      scope: '', active: '', waiting: false, controlled: false, subscription: '', keyMatch: null, made: false, posted: false,
      problem: '', errors: {}, ua: '' };
    try {
      r.origin = location.origin;
      r.page = location.pathname + (new URLSearchParams(location.search).has('sheet') ? '?sheet' : '');
      r.frame = window.self !== window.top;
      r.top = (location.ancestorOrigins && location.ancestorOrigins.length) ? location.ancestorOrigins[location.ancestorOrigins.length - 1] : '';
      r.standalone = navigator.standalone === true || !!(window.matchMedia && matchMedia('(display-mode: standalone)').matches);
      r.ua = String(navigator.userAgent).slice(0, 120);
      await look(r, tap);
    } catch (e) {
      r.errors.check = said(e);
      if (!r.problem) r.problem = 'check';
    }
    try { timed(post('/direct/report', r)).catch(() => {}); } catch {}
    return r;
  }
  window.hqPush = { check };
})();
