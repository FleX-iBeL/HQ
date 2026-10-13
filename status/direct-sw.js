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
      icon: '/hq-icon-192.png', badge: '/hq-icon-192.png', data: { url: m.url || '/direct' },
    });
    for (const c of await self.clients.matchAll({ type: 'window' })) c.postMessage({ hq: 'direct' });
  })());
});

self.addEventListener('notificationclick', (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || '/direct';
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
