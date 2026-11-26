// api.js: the one way the page talks to the server. JSON in and out, never cached.
//
//   const data = await api.get('api/todo');                    // GET
//   await api.post('api/todo', { tick: 'Renew…' }, 'todo');     // POST, tag -> x-hq header
//
// The old server refuses a change without its x-hq header (one tag per kind: todo,
// calendar, notes, features, weather, here, games, ...); post() always sends it.
// A not-ok answer throws an ApiError { status, path, message, body }; a request that never
// reaches the server throws one with status 0 and marks the page offline.
// api.offline is true while the server can't be reached (or the browser says it's offline);
// api.onOffline(fn) calls fn(true|false) on every change and returns a function to stop.
// Paths are relative ('api/todo'), so the page works under any prefix the server gives it.

export class ApiError extends Error {
  constructor(status, path, message, body) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.path = path;
    this.body = body;
  }
}

const listeners = new Set();
let offline = typeof navigator !== 'undefined' && navigator.onLine === false;

function setOffline(v) {
  if (v === offline) return;
  offline = v;
  for (const fn of listeners) { try { fn(v); } catch (e) { console.error(e); } }
}

async function request(method, path, body, tag) {
  const headers = { accept: 'application/json' };
  if (body !== undefined) headers['content-type'] = 'application/json';
  if (tag) headers['x-hq'] = tag;
  let r;
  try {
    r = await fetch(path, { method, cache: 'no-store', headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch (err) {
    setOffline(true);
    throw new ApiError(0, path, 'The server can’t be reached', null);
  }
  setOffline(false);
  const text = await r.text();
  let data = text;
  try { data = text ? JSON.parse(text) : null; } catch (e) { /* not JSON: keep the text */ }
  if (!r.ok) {
    const why = (data && typeof data === 'object' && (data.error || data.message)) || (typeof data === 'string' && data.trim()) || r.statusText;
    throw new ApiError(r.status, path, why || ('HTTP ' + r.status), data);
  }
  return data;
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, body, tag) => request('POST', path, body === undefined ? {} : body, tag),
  get offline() { return offline; },
  onOffline(fn) { listeners.add(fn); return () => listeners.delete(fn); }
};

if (typeof window !== 'undefined') {
  window.addEventListener('online', () => setOffline(false));
  window.addEventListener('offline', () => setOffline(true));
}
