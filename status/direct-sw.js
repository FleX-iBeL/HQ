// H80: the direct line's service worker. A push from HQ shows as a text from her on the lock screen; a tap opens
// the chat (/direct) in the HQ app. Served at /direct-sw.js with scope /, so it covers /hq and /direct alike.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

// F102: what the worker saw of a push goes to the status server (direct_line.py info), so "accepted by Apple, nothing on
// the phone" can be told apart from "the phone got it". The report can never stop the notification: it comes after it,
// and at most waits a moment.
const told = (what) => Promise.race([
  fetch('/direct/report', { method: 'POST', headers: { 'x-hq': 'direct', 'content-type': 'application/json' },
    body: JSON.stringify({ kind: 'push', ...what }) }).catch(() => {}),
  new Promise((done) => setTimeout(done, 2500)),
]);

self.addEventListener('push', (e) => {
  let m = {};
  try { m = e.data ? e.data.json() : {}; } catch { m = { body: e.data ? e.data.text() : '' }; }
  e.waitUntil((async () => {
    const title = m.title || 'HQ';
    let shown = 'yes', error = '';
    try {
      await self.registration.showNotification(title, {
        body: m.body || '', tag: m.tag || 'hq-direct', renotify: true,
        icon: '/hq-icon-192.png', badge: '/hq-icon-192.png', data: { url: m.url || '/direct', ring: m.ring || 0, agent: m.agent || '' },
        // H238: an agent calling him stays until he taps it or swipes it away
        ...(m.ring ? { requireInteraction: true } : {}),
      });
    } catch (err) {
      // F102: refused as asked, it still shows, plainly: a push that shows nothing costs the phone its subscription
      error = String(err).slice(0, 160);
      try {
        await self.registration.showNotification(title, { body: m.body || '', data: { url: m.url || '/direct' } });
        shown = 'plain';
      } catch (err2) {
        shown = 'no';
        error = (error + ' / ' + String(err2)).slice(0, 160);
      }
    }
    try {
      for (const c of await self.clients.matchAll({ type: 'window' })) c.postMessage({ hq: 'direct' });
    } catch {}
    await told({ shown, error, tag: m.tag || '' });
  })());
});

// F102: when the push service moves a phone to a new address the worker signs it up there by itself; without this the
// list keeps the old address until the next open.
self.addEventListener('pushsubscriptionchange', (e) => {
  e.waitUntil((async () => {
    try {
      const sub = e.newSubscription || await self.registration.pushManager.subscribe(e.oldSubscription ? e.oldSubscription.options : { userVisibleOnly: true,
        applicationServerKey: (await (await fetch('/direct/key', { cache: 'no-store' })).json()).key });
      await fetch('/direct/subscribe', { method: 'POST', headers: { 'x-hq': 'direct', 'content-type': 'application/json' },
        body: JSON.stringify({ subscription: sub.toJSON(), device: 'moved by the service worker' }) });
      await told({ shown: 'moved', error: '', tag: String(sub.endpoint).slice(-14) });
    } catch (err) {
      await told({ shown: 'move failed', error: String(err).slice(0, 160), tag: '' });
    }
  })());
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const d = e.notification.data || {};
  let url = d.url || '/direct';
  // H238: "<agent> is calling": the call page starts that call. On the call line's own address (8443, or 7860 on the
  // Mac) the call page is /; on the HQ page's address (8444, or 4748) it's inside /hq, which passes ?ring on.
  if (d.ring) {
    const q = '?ring=' + encodeURIComponent(d.ring) + '&agent=' + encodeURIComponent(d.agent || '');
    url = (self.location.port === '8443' || self.location.port === '7860' ? '/' : '/hq') + q;
  }
  e.waitUntil((async () => {
    for (const c of await self.clients.matchAll({ type: 'window', includeUncontrolled: true })) {
      if ('focus' in c) {
        try { await c.navigate(url); } catch {}
        return c.focus();
      }
    }
    return self.clients.openWindow(url);
  })());
});
