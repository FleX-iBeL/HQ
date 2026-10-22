// H80: the direct line's service worker. A push from HQ shows as a text from her on the lock screen; a tap opens
// the chat (/direct) in the HQ app. Served at /direct-sw.js with scope /, so it covers /hq and /direct alike.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()));

self.addEventListener('push', (e) => {
  let m = {};
  try { m = e.data ? e.data.json() : {}; } catch { m = { body: e.data ? e.data.text() : '' }; }
  e.waitUntil((async () => {
    await self.registration.showNotification(m.title || 'HQ', {
      body: m.body || '', tag: m.tag || 'hq-direct', renotify: true,
      icon: '/hq-icon-192.png', badge: '/hq-icon-192.png', data: { url: m.url || '/direct', ring: m.ring || 0, agent: m.agent || '' },
      // H238: an agent calling him stays until he taps it or swipes it away
      ...(m.ring ? { requireInteraction: true } : {}),
    });
    for (const c of await self.clients.matchAll({ type: 'window' })) c.postMessage({ hq: 'direct' });
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
