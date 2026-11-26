// Spotlight on the phone: her panel pulls up into her space and back down, and a sideways swipe
// on her home moves to the next or previous agent. Only motion: the screen changes at the start
// of each move (as a tap does), and a move let go too early puts it back. Not in demo mode.
//
// The templates mark the parts: data-g="home" (her home), "stage" (her face, name and Call),
// "pullup" (the panel at the bottom of home), "space" (her space), "space-head" (its top bar),
// "pulldown" (its panel), and data-g-act="open" / "close" on what opens or closes it with a tap.
import { rerenderAll, holdRenders } from '../engine.js';

const DUR = 280, FADE = 150, EASE = 'cubic-bezier(0.22, 1, 0.36, 1)';
const SLOP = 8, EDGE = 24, PULL_AT = 0.35, FLICK = 0.5; // px, px, share of the way, px per ms
let app = null, on = false, busy = false;

const q = (g) => document.querySelector('[data-g="' + g + '"]');
const reduced = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches;
const active = () => on && app && !app.demoMode && app.device === 'phone' && app.state.design === 'spotlight' && !busy;
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// What the engine wrote last is put back, so nothing of a move stays on a node.
function restore(el) { if (el && el.__a) { if (el.__a.style) el.setAttribute('style', el.__a.style); else el.removeAttribute('style'); } }
function cloneOf(el) {
  const c = el.cloneNode(true);
  for (const n of [c, ...c.querySelectorAll('[id]')]) n.removeAttribute('id');
  for (const n of c.querySelectorAll('[data-g]')) n.dataset.gc = n.dataset.g;
  for (const n of [c, ...c.querySelectorAll('[data-g]')]) n.removeAttribute('data-g');
  c.setAttribute('aria-hidden', 'true');
  c.inert = true;
  const r = el.getBoundingClientRect(), pr = el.parentElement.getBoundingClientRect();
  Object.assign(c.style, { position: 'absolute', left: (r.left - pr.left) + 'px', top: (r.top - pr.top) + 'px', width: r.width + 'px', height: r.height + 'px',
    margin: '0', pointerEvents: 'none', boxSizing: 'border-box' });
  return c;
}
// A frame, or a short timer when the page gets no frames (hidden), so a move always ends.
const frame = (fn) => { let ran = false; const go = (t) => { if (!ran) { ran = true; fn(t || performance.now()); } }; requestAnimationFrame(go); setTimeout(() => go(performance.now()), 50); };
// Run t from a to b over the duration with the ease, calling set(t); then done().
function tween(a, b, set, done, ms) {
  const d = reduced() ? 1 : (ms || DUR);
  if (typeof document !== 'undefined' && document.hidden) { set(b); done(); return; } // no frames while hidden
  const t0 = performance.now();
  const ease = (x) => 1 - Math.pow(1 - x, 3);
  const step = (now) => {
    const x = clamp((now - t0) / d, 0, 1);
    set(a + (b - a) * ease(x));
    if (x < 1) frame(step); else done();
  };
  frame(step);
}

// ---- up: home's panel becomes her space ----------------------------------------------------
function beginUp() {
  const home = q('home'), panel = q('pullup');
  if (!home || !panel) return null;
  const from = panel.getBoundingClientRect().top;
  const was = { screen: app.state.screen, stack: app.state.stack };
  const ghost = cloneOf(home);
  const release = holdRenders();
  app.go(app.state.space, { space: app.state.space });
  rerenderAll();
  const sp = q('space'), head = q('space-head'), body = q('pulldown');
  if (!sp || !head || !body) { ghost.remove(); release(); return null; }
  sp.parentElement.insertBefore(ghost, sp);
  ghost.style.zIndex = '0';
  sp.style.position = 'relative'; sp.style.zIndex = '1'; sp.style.background = 'transparent';
  const gPanel = ghost.querySelector('[data-gc="pullup"]'), gStage = ghost.querySelector('[data-gc="stage"]');
  const dist = Math.max(1, from - body.getBoundingClientRect().top);
  body.style.willChange = 'transform';
  const set = (t) => {
    body.style.transform = 'translateY(' + (dist * (1 - t)) + 'px)';
    head.style.opacity = String(t);
    ghost.style.opacity = String(1 - t);
    if (gStage) gStage.style.transform = 'scale(' + (1 - 0.06 * t) + ')';
    if (gPanel) { gPanel.style.transform = 'translateY(' + (-dist * t) + 'px)'; gPanel.style.opacity = String(clamp(1 - 4 * t, 0, 1)); }
  };
  set(0);
  const clean = () => { ghost.remove(); for (const el of [sp, head, body]) restore(el); release(); busy = false; };
  return {
    dist, set,
    end(keep) {
      busy = true;
      if (reduced()) { set(keep ? 1 : 0); if (!keep) { app.setState(was); rerenderAll(); } clean(); return; }
      tween(cur, keep ? 1 : 0, set, () => { if (!keep) { app.setState(was); rerenderAll(); } clean(); });
    }
  };
}

// ---- down: her space goes back to her home -------------------------------------------------
function beginDown() {
  const sp = q('space'), body = q('pulldown');
  if (!sp || !body) return null;
  const scrolled = body.scrollTop;
  const was = { screen: app.state.screen, stack: app.state.stack };
  const ghost = cloneOf(sp);
  const release = holdRenders();
  app.back();
  rerenderAll();
  const home = q('home'), panel = q('pullup'), stage = q('stage');
  if (!home || !panel) { release(); return null; }
  home.parentElement.appendChild(ghost);
  ghost.style.zIndex = '5'; ghost.style.background = 'transparent';
  const gHead = ghost.querySelector('[data-gc="space-head"]'), gBody = ghost.querySelector('[data-gc="pulldown"]');
  if (gBody) gBody.scrollTop = scrolled;
  panel.style.visibility = 'hidden';
  const dist = Math.max(1, panel.getBoundingClientRect().top - body.getBoundingClientRect().top);
  if (gBody) gBody.style.willChange = 'transform';
  const set = (t) => {
    if (gBody) gBody.style.transform = 'translateY(' + (dist * t) + 'px)';
    if (gHead) gHead.style.opacity = String(1 - t);
    if (stage) { stage.style.opacity = String(t); stage.style.transform = 'scale(' + (0.94 + 0.06 * t) + ')'; }
  };
  set(0);
  const clean = () => { ghost.remove(); for (const el of [panel, stage]) restore(el); release(); busy = false; };
  return {
    dist, set,
    end(keep) {
      busy = true;
      const finish = () => {
        if (!keep) { app.setState(was); rerenderAll(); clean(); return; }
        // the space's rows fade into home's panel, which comes up under them
        panel.style.visibility = ''; panel.style.opacity = '0';
        tween(0, 1, (x) => { panel.style.opacity = String(x); ghost.style.opacity = String(1 - x); }, clean, FADE);
      };
      if (reduced()) { set(keep ? 1 : 0); finish(); return; }
      tween(cur, keep ? 1 : 0, set, finish);
    }
  };
}

// ---- sideways: the next or previous agent --------------------------------------------------
function slideTo(dir, fromX) {
  const stage = q('stage');
  if (!stage) return;
  busy = true;
  const w = stage.getBoundingClientRect().width || 390;
  const release = holdRenders();
  tween(fromX || 0, -dir * w, (x) => { stage.style.transform = 'translateX(' + x + 'px)'; stage.style.opacity = String(1 - Math.abs(x) / w); }, () => {
    restore(stage);
    const v = app.renderVals();
    (dir > 0 ? v.spotNext : v.spotPrev)();
    rerenderAll();
    const next = q('stage');
    if (!next) { release(); busy = false; return; }
    tween(dir * w * 0.35, 0, (x) => { next.style.transform = 'translateX(' + x + 'px)'; next.style.opacity = String(1 - Math.abs(x) / (w * 0.35)); },
      () => { restore(next); release(); busy = false; }, 220);
  }, reduced() ? 1 : 200);
}

// ---- the pointer ---------------------------------------------------------------------------
let g = null, cur = 0, eatClick = false;
function down(e) {
  if (!active() || g || (e.pointerType === 'mouse' && e.button !== 0)) return;
  const t = e.target;
  if (t.closest('input, textarea, select, [contenteditable]')) return;
  const inPanel = t.closest('[data-g="pullup"]'), inHome = t.closest('[data-g="home"]');
  const inHead = t.closest('[data-g="space-head"], [data-g="handle"]');
  const inBody = t.closest('[data-g="pulldown"]');
  let kind = null;
  if (inPanel) kind = 'up';
  else if (inHome) kind = e.clientX > EDGE && e.clientX < window.innerWidth - EDGE ? 'side' : null;
  else if (inHead) kind = 'down';
  else if (inBody && inBody.scrollTop <= 0 && t.closest('[data-g="handle"]')) kind = 'down';
  if (!kind) return;
  g = { kind, id: e.pointerId, x0: e.clientX, y0: e.clientY, axis: null, run: null, pts: [[e.timeStamp, e.clientX, e.clientY]], el: t };
}
function move(e) {
  if (!g || e.pointerId !== g.id) return;
  const dx = e.clientX - g.x0, dy = e.clientY - g.y0;
  g.pts.push([e.timeStamp, e.clientX, e.clientY]); if (g.pts.length > 6) g.pts.shift();
  if (!g.axis) {
    if (Math.abs(dx) < SLOP && Math.abs(dy) < SLOP) return;
    g.axis = Math.abs(dy) >= Math.abs(dx) ? 'y' : 'x';
    const fits = (g.kind === 'side' && g.axis === 'x') || (g.kind === 'up' && g.axis === 'y' && dy < 0) || (g.kind === 'down' && g.axis === 'y' && dy > 0);
    // her home: a vertical pull anywhere on it lifts the panel too
    if (!fits && g.kind === 'side' && g.axis === 'y' && dy < 0) g.kind = 'up';
    else if (!fits) { g = null; return; }
    try { g.el.setPointerCapture && document.documentElement.setPointerCapture(e.pointerId); } catch (x) { /* fine */ }
    if (g.kind === 'up') g.run = beginUp();
    else if (g.kind === 'down') g.run = beginDown();
    if (g.kind !== 'side' && !g.run) { g = null; return; }
    eatClick = true;
  }
  e.preventDefault();
  if (g.kind === 'side') {
    const st = q('stage'); if (st) { st.style.transform = 'translateX(' + dx + 'px)'; st.style.opacity = String(1 - Math.min(0.6, Math.abs(dx) / 600)); }
    return;
  }
  cur = clamp(g.kind === 'up' ? -dy / g.run.dist : dy / g.run.dist, 0, 1);
  g.run.set(cur);
}
function speed(was) {
  const p = was.pts, a = p[0], b = p[p.length - 1], dt = Math.max(1, b[0] - a[0]);
  return { vx: (b[1] - a[1]) / dt, vy: (b[2] - a[2]) / dt };
}
function up(e) {
  if (!g || e.pointerId !== g.id) return;
  const was = g; g = null;
  if (!was.axis) return; // a tap: the click does it
  const { vx, vy } = speed(was);
  if (was.kind === 'side') {
    const dx = e.clientX - was.x0, w = window.innerWidth;
    const st = q('stage');
    if (Math.abs(dx) > w * 0.22 || Math.abs(vx) > FLICK) slideTo(dx < 0 ? 1 : -1, dx);
    else if (st) { busy = true; tween(dx, 0, (x) => { st.style.transform = 'translateX(' + x + 'px)'; }, () => { restore(st); busy = false; }, 180); }
  } else {
    const flick = was.kind === 'up' ? -vy : vy;
    was.run.end(flick > FLICK || (flick > -FLICK / 2 && cur > PULL_AT));
  }
  setTimeout(() => { eatClick = false; }, 0);
}
function cancel(e) { if (g && e.pointerId === g.id) { const was = g; g = null; if (was.run) was.run.end(false); else restore(q('stage')); } }
// A tap on what opens or closes her space moves the same way.
function click(e) {
  if (eatClick) { eatClick = false; e.preventDefault(); e.stopPropagation(); return; }
  if (!active()) return;
  const a = e.target.closest('[data-g-act]');
  if (!a) return;
  e.preventDefault(); e.stopPropagation();
  const run = a.dataset.gAct === 'open' ? beginUp() : beginDown();
  if (run) { cur = 0; run.end(true); }
}
function key(e) {
  if (!g || e.key !== 'Escape') return;
  const was = g; g = null;
  if (was.run) was.run.end(false); else restore(q('stage'));
}

export function install(theApp) {
  app = theApp;
  if (on || typeof document === 'undefined') return;
  on = true;
  document.addEventListener('pointerdown', down, true);
  document.addEventListener('pointermove', move, { capture: true, passive: false });
  document.addEventListener('pointerup', up, true);
  document.addEventListener('pointercancel', cancel, true);
  document.addEventListener('click', click, true);
  document.addEventListener('keydown', key, true);
}
