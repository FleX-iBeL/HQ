// boot.js: picks the device and the design, loads their templates and stylesheets, and
// mounts the app. The device follows the window (phone below 820 px wide, Mac above) and
// is picked again on resize or rotate; the design comes from ?design= (for testing),
// else localStorage hq-design, else the manifest's default. Switching either mounts the
// other templates with the same component, so the state is kept.
import { compile, mount } from './engine.js';
import { Component } from './app.js';

const PHONE_BELOW = 820;
const cache = new Map();
const text = (path) => {
  if (!cache.has(path)) cache.set(path, fetch(path).then((r) => { if (!r.ok) throw new Error(path + ': ' + r.status); return r.text(); }));
  return cache.get(path);
};
const store = {
  get() { try { return localStorage.getItem('hq-design'); } catch (e) { return null; } },
  set(v) { try { localStorage.setItem('hq-design', v); } catch (e) { /* private mode: only for this visit */ } }
};
const deviceFor = () => (window.innerWidth < PHONE_BELOW ? 'phone' : 'mac');

let manifest, app, component, now = { device: null, design: null }, turn = 0;

function pickDesign() {
  const asked = new URLSearchParams(location.search).get('design');
  for (const d of [asked, store.get(), manifest.default]) if (d && manifest.designs.includes(d)) return d;
  return manifest.designs[0];
}

// The stylesheets for this device and design, put in before the old ones go, so nothing
// flashes. A sheet already there is never moved (moving a <link> loads it again).
function styles(list) {
  const old = [...document.querySelectorAll('link[data-hq]')];
  const keep = new Set();
  let prev = null;
  const loads = list.map((href) => {
    let l = old.find((x) => x.getAttribute('href') === href);
    let load = Promise.resolve();
    if (l) keep.add(l);
    else {
      l = document.createElement('link');
      l.rel = 'stylesheet'; l.href = href; l.dataset.hq = '';
      load = new Promise((ok) => { l.onload = l.onerror = ok; });
      if (prev) prev.after(l);
      else if (old.length) old[0].before(l);
      else document.head.appendChild(l);
    }
    prev = l;
    return load;
  });
  return Promise.all(loads).then(() => old.forEach((l) => { if (!keep.has(l)) l.remove(); }));
}

async function show(device, design) {
  const mine = ++turn;
  const m = manifest.devices[device].designs[design];
  const files = { shell: m.shell };
  for (const [name, p] of Object.entries(m.screens)) files[name] = p;
  const loaded = {};
  await Promise.all(Object.entries(files).map(async ([k, p]) => { loaded[k] = await text('templates/' + p); }));
  await styles([m.fonts].concat(m.css, ['css/fluid-' + device + '.css']));
  if (mine !== turn) return; // a newer switch came in meanwhile
  const tpl = compile(loaded.shell, { include: (name) => { if (!(name in loaded)) throw new Error('No screen ' + name); return loaded[name]; } });
  const container = document.getElementById('app');
  if (app) app.unmount();
  component.device = device;
  component.state = Object.assign({}, component.state, { design });
  app = mount(container, tpl, component, { onError: (err, where) => (window.HQ.onError || ((e, w) => console.error('HQ:', w, e)))(err, where) });
  now = { device, design };
  document.documentElement.dataset.device = device;
  document.documentElement.dataset.design = design;
  window.HQ.app = app;
}

function useDesign(design) {
  if (!manifest.designs.includes(design) || design === now.design) return;
  store.set(design);
  const url = new URL(location.href);
  if (url.searchParams.has('design')) { url.searchParams.set('design', design); history.replaceState(null, '', url); }
  show(now.device, design);
}

async function boot() {
  manifest = JSON.parse(await text('templates/manifest.json'));
  const design = pickDesign();
  // Demo mode: ?demo=1 (or localStorage hq-demo = 1) shows the design-review rows in Settings.
  let demo = new URLSearchParams(location.search).get('demo') === '1';
  try { demo = demo || localStorage.getItem('hq-demo') === '1'; } catch (e) { /* no storage */ }
  component = new Component({ design, device: deviceFor(), onDesign: useDesign, demo });
  Object.assign(window.HQ, { component, manifest, useDesign, show, now: () => now, app: null });
  await show(deviceFor(), design);
  let wait = 0;
  const again = () => { clearTimeout(wait); wait = setTimeout(() => { const d = deviceFor(); if (d !== now.device) show(d, now.design); }, 120); };
  window.addEventListener('resize', again);
  window.addEventListener('orientationchange', again);
}

window.HQ = {};
window.HQ.ready = boot().catch((err) => { console.error('HQ did not start:', err); document.getElementById('app').textContent = 'HQ did not start: ' + err.message; });
