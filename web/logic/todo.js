// The to-do area (Donna): the four boxes, the full list behind a box, an item (plan it in,
// comes back, move, let go, tick off, rename), the done and let-go lists, the undo line,
// groceries and ticked-off groceries (the groceries tab of the lists screen).
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data
// (GET api/todo as the server gives it; changes go to POST api/todo with x-hq: todo).
import * as demo from './demo/todo.js';
import { holdRenders, rerenderAll } from '../engine.js';
import { chip, flip, tick } from './util.js';

export const NAME = 'todo';
export const WIRED = true;
export const LOADING_OK = true;
export { demo };

// tdList / tdItem: the real list key and item id that are open; tdErr: the first load failed;
// tdAdd: what's typed in a list's add box.
export const start = { item: null, itemDone: false, bought: {}, todoBox: 'Important, not urgent', listKind: 'box', todoFilter: 'all', planned: null, repeat: 'Doesn’t repeat',
  tdList: null, tdItem: null, tdErr: false, tdAdd: '' };

const FILTER_KEY = 'hq-todo-filter';
const REPEATS = [['off', 'Doesn’t repeat'], ['every week', 'Every week'], ['every month', 'Every month'], ['every quarter', 'Every quarter'], ['every year', 'Every year']];
// The four boxes in the design's order, and how each one looks.
const QUADS = [
  { kind: 'q1', name: 'Urgent and important', cc: '#b42318', shadow: '0 0 0 1px #e2e8f0 inset', op: 1 },
  { kind: 'q2', name: 'Important, not urgent', cc: '#0f172a', shadow: '0 0 0 2px #0f172a inset', op: 1 },
  { kind: 'q3', name: 'Urgent, not important', cc: '#0f172a', shadow: '0 0 0 1px #e2e8f0 inset', op: 1 },
  { kind: 'q4', name: 'Neither', cc: '#0f172a', shadow: '0 0 0 1px #e2e8f0 inset', op: 0.6 }
];
const OPEN_KINDS = ['commit', 'q1', 'q2', 'q3', 'q4'];

// ---- talking to the server -------------------------------------------------------------

export async function load(app) {
  try {
    const d = await app.api.get('api/todo');
    app.setData('todo', d);
    if (app.state.tdErr) app.setState({ tdErr: false });
  } catch (err) {
    if (!app.state.data.todo) app.setState({ tdErr: true });
    throw err;
  }
}

// The filter of a list (all, planned, not planned), remembered on this device as the old page does.
function savedFilter() {
  try { const v = localStorage.getItem(FILTER_KEY); return ['all', 'planned', 'open'].includes(v) ? v : 'all'; } catch (e) { return 'all'; }
}

export const enter = {
  todo: (app) => load(app),
  todoList: (app) => { app.setState({ todoFilter: savedFilter() }); return load(app); },
  lists: (app) => load(app)
};

// A change: shown at once (patch), then the list as the server has it, with its words and
// its Undo (undone: what to do once the undo went through). A refusal puts the server's list
// back and says why.
async function send(app, body, patch, undone) {
  if (patch) app.setData('todo', (d) => (d && Array.isArray(d.lists) ? patch(JSON.parse(JSON.stringify(d))) || d : d));
  try {
    const d = await app.api.post('api/todo', body, 'todo');
    if (d && Array.isArray(d.lists)) app.setData('todo', d);
    const undo = d && d.undo ? () => send(app, { undo: true }).then((r) => { if (r && undone) undone(r); }) : null;
    if (d && d.said) app.say(d.said, undo);
    return d;
  } catch (err) {
    app.say(err && err.status === 0 ? 'Couldn’t reach HQ. Try again.' : ((err && err.message) || 'Couldn’t change the list. Try again.'));
    load(app).catch(() => {});
    return null;
  }
}

// ---- reading the real data -------------------------------------------------------------

const listsOf = (d) => (d && Array.isArray(d.lists) ? d.lists : []);
const byKind = (d, k) => listsOf(d).filter((l) => l.kind === k);
const byKey = (d, k) => listsOf(d).find((l) => l.key === k) || null;
function findItem(d, id) {
  for (const l of listsOf(d)) { const it = l.items.find((x) => x.id === id); if (it) return [l, it]; }
  return [null, null];
}
const without = (d, id) => { for (const l of listsOf(d)) l.items = l.items.filter((x) => x.id !== id); return d; };

// A deadline date within the next week shows in red (as the old page does).
function soon(dl) {
  const m = /(\d{4}-\d\d-\d\d)/.exec(dl || ''); if (!m) return false;
  return Date.parse(m[1] + 'T23:59:00') - Date.now() < 7 * 864e5;
}
const planWords = (pl) => (pl ? 'Planned ' + pl.short + (pl.past ? ' (gone by)' : '') : '');
function metaOf(it, closed, kind) {
  const at = it.at ? (kind === 'done' ? 'Done ' : kind === 'letgo' ? 'Let go ' : '') + it.at : '';
  const p = [it.for ? 'For ' + it.for : '', it.deadline ? 'Deadline ' + it.deadline : '', it.status && it.status !== 'open' ? it.status : '',
    it.calendar ? 'In the calendar: ' + it.calendar : '', at, it.often];
  if (!closed && it.repeats) p.push('Repeats ' + it.repeats);
  if (!closed && it.planned) p.push(planWords(it.planned) + ' · ' + it.planned.title);
  return p.filter(Boolean).join(' · ');
}
function shortDate(s) {
  const m = /(\d{4})-(\d\d)-(\d\d)/.exec(s || ''); if (!m) return s || '';
  return new Date(+m[1], +m[2] - 1, +m[3]).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}
function blockWhen(b) {
  const s = new Date(b.start), e = new Date(b.end);
  const t = (x) => x.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' });
  return s.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' }) + ' · ' + t(s) + ' to ' + t(e) + (b.calendar && b.calendar !== 'Main' ? ' · ' + b.calendar : '');
}

// ---- the drag that changes the order (the grip, or a long press on the row) ---------------

function scroller(node) {
  for (let n = node.parentElement; n; n = n.parentElement) {
    const o = getComputedStyle(n).overflowY;
    if ((o === 'auto' || o === 'scroll') && n.scrollHeight > n.clientHeight) return n;
  }
  return document.scrollingElement;
}
const HOLD_MS = 300, SLOP = 8, EASE_MS = 160;
let dragging = null, eatClick = false, hooked = false;
// While a row is dragged the page must not scroll under the finger (a touch that began on the row, not
// on the grip, has no touch-action of its own), and the click that ends a long press opens nothing.
function hookOnce() {
  if (hooked || typeof document === 'undefined') return;
  hooked = true;
  document.addEventListener('touchmove', (e) => { if (dragging) e.preventDefault(); }, { passive: false });
  document.addEventListener('click', (e) => { if (eatClick) { eatClick = false; e.preventDefault(); e.stopPropagation(); } }, true);
  document.addEventListener('contextmenu', (e) => { if (dragging || pressing) e.preventDefault(); }, true);
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && dragging) { e.preventDefault(); dragging.cancel(); } }, true);
}
let pressing = null;
// The row under the finger is lifted and follows it; the others slide to open a gap; near the top or
// bottom of the list's scroller the list scrolls along. On release the row settles into the gap and
// done(from, to) gets the places as shown. Escape, a pointer cancel, or the pointer far to the side
// of the list puts everything back. No render reaches the list while it moves.
function drag(row, pointer, y, done) {
  const box = row && row.parentNode;
  if (!box) return;
  const rows = [...box.children].filter((r) => r.classList.contains('row'));
  const from = rows.indexOf(row); if (from < 0) return;
  hookOnce();
  const release = holdRenders();
  try { row.setPointerCapture(pointer); } catch (_) { /* fine without */ }
  const sc = scroller(box), tops = rows.map((r) => r.offsetTop), hs = rows.map((r) => r.offsetHeight);
  const gap = rows.length > 1 ? Math.max(0, (rows[1].offsetTop - rows[0].offsetTop) - hs[0]) : 0;
  const d = { y, y0: y, x: 0, s0: sc.scrollTop, to: from, raf: 0, out: false };
  const lift = { position: 'relative', zIndex: '3', background: '#ffffff', boxShadow: '0 10px 28px rgba(15,23,42,0.18)', transition: 'box-shadow .15s ease-out' };
  Object.assign(row.style, lift);
  for (const r of rows) if (r !== row) r.style.transition = 'transform .16s ease-out';
  const shiftOf = (i) => (i > from && i <= d.to) ? -(hs[from] + gap) : (i < from && i >= d.to) ? hs[from] + gap : 0;
  const layout = () => {
    const dy = d.y - d.y0 + (sc.scrollTop - d.s0), mid = tops[from] + dy + hs[from] / 2;
    let to = from;
    for (let i = 0; i < rows.length; i++) {
      if (i < from && mid < tops[i] + hs[i] / 2) { to = i; break; }
      if (i > from && mid > tops[i] + hs[i] / 2) to = i;
    }
    d.to = d.out ? from : to;
    row.style.transform = 'translateY(' + dy + 'px) scale(1.02)';
    row.style.opacity = d.out ? '0.6' : '';
    rows.forEach((r, i) => { if (r !== row) { const sh = shiftOf(i); r.style.transform = sh ? 'translateY(' + sh + 'px)' : ''; } });
  };
  const edge = () => {
    const r = sc === document.scrollingElement ? { top: 0, bottom: window.innerHeight } : sc.getBoundingClientRect();
    const zone = 56;
    const v = d.y < r.top + zone ? -Math.ceil((r.top + zone - d.y) / 6) : d.y > r.bottom - zone ? Math.ceil((d.y - r.bottom + zone) / 6) : 0;
    if (v) { const was = sc.scrollTop; sc.scrollTop += v; if (sc.scrollTop !== was) layout(); }
    d.raf = requestAnimationFrame(edge);
  };
  d.raf = requestAnimationFrame(edge);
  const boxRect = box.getBoundingClientRect();
  const move = (ev) => { if (ev.pointerId !== pointer) return; ev.preventDefault(); d.y = ev.clientY; d.out = ev.clientX < boxRect.left - 120 || ev.clientX > boxRect.right + 120; layout(); };
  const off = () => {
    document.removeEventListener('pointermove', move, true); document.removeEventListener('pointerup', up, true); document.removeEventListener('pointercancel', cancel, true);
    cancelAnimationFrame(d.raf);
    dragging = null;
  };
  const clear = () => {
    for (const r of rows) { r.style.transition = ''; r.style.transform = ''; }
    for (const k of ['position', 'zIndex', 'background', 'boxShadow', 'transition', 'transform', 'opacity']) row.style[k] = '';
  };
  const cancel = () => { off(); d.to = from; clear(); release(); };
  const up = (ev) => {
    if (ev.pointerId !== pointer) return;
    off();
    const to = d.to;
    // settle into the gap, then the list takes the new order in one go
    let target = 0;
    for (let i = Math.min(from, to); i <= Math.max(from, to); i++) if (i !== from) target += (to > from ? 1 : -1) * (hs[i] + gap);
    row.style.transition = 'transform ' + EASE_MS + 'ms cubic-bezier(0.22, 1, 0.36, 1), box-shadow .15s ease-out';
    row.style.transform = 'translateY(' + target + 'px)';
    row.style.boxShadow = '';
    setTimeout(() => {
      if (to !== from) done(from, to);
      rerenderAll();
      clear();
      release();
    }, EASE_MS);
  };
  document.addEventListener('pointermove', move, true); document.addEventListener('pointerup', up, true); document.addEventListener('pointercancel', cancel, true);
  dragging = { cancel };
  layout();
}
// The grip: the drag starts at once.
function startDrag(e, done) {
  if (e.button !== 0 || dragging) return;
  e.preventDefault();
  eatClick = false;
  drag(e.currentTarget.closest('.row'), e.pointerId, e.clientY, done);
}
// The row itself: held still for about 300 ms it is picked up; a tap still opens it, a swipe still scrolls.
function pressRow(e, done) {
  if (e.button !== 0 || dragging || pressing) return;
  if (e.target.closest('input, textarea, [role="button"][aria-label^="Change the order"], button[aria-label^="Tick off"], .small')) return;
  hookOnce();
  const row = e.currentTarget, id = e.pointerId, x0 = e.clientX, y0 = e.clientY;
  let y = y0;
  const stop = () => {
    clearTimeout(pressing && pressing.t);
    document.removeEventListener('pointermove', mv, true); document.removeEventListener('pointerup', stop, true); document.removeEventListener('pointercancel', stop, true);
    pressing = null;
  };
  const mv = (ev) => { if (ev.pointerId !== id) return; y = ev.clientY; if (Math.abs(ev.clientX - x0) > SLOP || Math.abs(ev.clientY - y0) > SLOP) stop(); };
  pressing = { t: setTimeout(() => {
    stop();
    eatClick = true;
    try { if (navigator.vibrate) navigator.vibrate(15); } catch (_) { /* no buzz */ }
    drag(row, id, y, done);
  }, HOLD_MS) };
  document.addEventListener('pointermove', mv, true); document.addEventListener('pointerup', stop, true); document.addEventListener('pointercancel', stop, true);
}

// ---- the values ------------------------------------------------------------------------

export function vals(st, ctx, D) {
  return D === demo ? demoVals(st, ctx, D) : realVals(st, ctx, D);
}

// Real data, shaped for the design's screens.
function realVals(st, ctx, D) {
  const { app } = ctx;
  const d = D && Array.isArray(D.lists) ? D : null;
  const off = !!(D && D.off);
  const loading = !d && !off && !st.tdErr;
  const retry = () => { app.setState({ tdErr: false }); load(app).catch(() => {}); };
  const openItem = (l, it) => () => app.go('todoItem', { tdItem: it.id, tdList: l.key });
  const openList = (key) => () => app.go('todoList', { tdList: key, listKind: 'box', todoFilter: savedFilter() });

  // Overview: what's promised to others, the four boxes, the other lists' counts
  const commit = byKind(d, 'commit');
  const cItems = commit.flatMap((l) => l.items);
  const boxes = QUADS.map((q) => {
    const ls = byKind(d, q.kind), items = ls.flatMap((l) => l.items.map((it) => [l, it]));
    return {
      name: ls.length ? ls.map((l) => l.name).join(' + ') : q.name, count: items.length, cc: q.cc, shadow: q.shadow, op: q.op,
      openAll: ls.length ? openList(ls[0].key) : () => {},
      more: items.length > 2 ? '+ ' + (items.length - 2) + ' more' : 'See the list',
      items: items.slice(0, 2).map(([l, it]) => ({ title: it.title, open: openItem(l, it) }))
    };
  });
  const openCount = listsOf(d).filter((l) => OPEN_KINDS.includes(l.kind)).reduce((n, l) => n + l.items.length, 0);
  const groceriesL = byKind(d, 'groceries')[0] || null, tickedL = byKind(d, 'grocoff')[0] || null;
  const doneL = byKind(d, 'done')[0] || null, letgoL = byKind(d, 'letgo')[0] || null;
  const empty = !!d && !openCount && !(groceriesL && groceriesL.items.length);

  // The list behind a box, or Done, or Let go
  let l = d ? byKey(d, st.tdList) : null;
  if (st.listKind === 'done') l = doneL; else if (st.listKind === 'letgo') l = letgoL;
  const closed = !!l && (l.kind === 'done' || l.kind === 'letgo');
  const canFilter = !!l && !closed && l.kind !== 'groceries' && l.kind !== 'grocoff' && l.items.length > 0;
  const show = canFilter ? st.todoFilter : 'all';
  const all = l ? l.items : [];
  const nPl = all.filter((x) => x.planned).length;
  const shown = all.filter((x) => show === 'all' || (show === 'planned' ? x.planned : !x.planned));
  const sortable = !!l && !closed && l.kind !== 'grocoff' && all.length > 1 && show === 'all';
  const place = (it, n) => send(app, { order: it.id, place: n }, (x) => {
    const ll = byKey(x, l.key); const i = ll ? ll.items.findIndex((y) => y.id === it.id) : -1;
    if (i >= 0) { const [m] = ll.items.splice(i, 1); ll.items.splice(n - 1, 0, m); }
    return x;
  });
  const todoRows = shown.map((it, i) => ({
    id: it.id, title: it.title, meta: metaOf(it, closed, l.kind),
    mc: !closed && soon(it.deadline) ? '#b42318' : '#475569',
    open: openItem(l, it),
    tick: () => send(app, l.kind === 'groceries' ? { tick: it.id } : { done: it.id }, (x) => without(x, it.id)),
    back: () => app.setState({ tdItem: it.id, sheet: 'move' }),
    grip: (e) => startDrag(e, (from, to) => place(it, to + 1)),
    press: sortable ? (e) => pressRow(e, (from, to) => place(it, to + 1)) : null,
    gripKey: (e) => {
      if (e.key === 'ArrowUp' && i > 0) { e.preventDefault(); place(it, i); }
      else if (e.key === 'ArrowDown' && i < shown.length - 1) { e.preventDefault(); place(it, i + 2); }
    }
  }));
  const todoFilters = canFilter ? [['all', 'All', all.length], ['planned', 'Planned', nPl], ['open', 'Not planned', all.length - nPl]].map((f) => {
    const on = show === f[0];
    return Object.assign({ name: f[1] + ' ' + f[2], on: on ? 'true' : 'false', pick: () => { try { localStorage.setItem(FILTER_KEY, f[0]); } catch (e) { /* only for now */ } app.setState({ todoFilter: f[0] }); } }, chip(on));
  }) : [];
  let listNote = '';
  if (!d) listNote = loading ? 'Getting your list…' : 'Your list didn’t load. Go back and try again.';
  else if (!l) listNote = 'This list isn’t there anymore.';
  else if (!all.length) listNote = 'Nothing here right now.';
  else if (!shown.length) listNote = show === 'planned' ? 'Nothing here is planned in the calendar yet.' : 'Everything here is planned.';
  // The add box takes several at once, one per line: Enter adds, Shift+Enter starts a new line
  const addKey = (e) => {
    if (e.key !== 'Enter' || e.shiftKey || e.isComposing) return;
    e.preventDefault();
    const t = (e.target.value || '').trim(); if (!t || !l) return;
    e.target.value = ''; e.target.style.height = '';
    app.setState({ tdAdd: '' });
    send(app, { add: t, list: l.key });
  };
  const addInput = (e) => { const ta = e.target; ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight, 140) + 'px'; app.quietState({ tdAdd: ta.value }, ta); };

  // One item
  const [il, it] = findItem(d, st.tdItem);
  const iClosed = !!il && (il.kind === 'done' || il.kind === 'letgo');
  const iGro = !!il && (il.kind === 'groceries' || il.kind === 'grocoff');
  const item = it ? { box: il.name, title: it.title } : { box: '', title: '' };
  const fields = it ? (it.fields || []).filter((f) => !/^(for|deadline)$/i.test(f[0])).map((f) => ({ k: f[0], v: f[1] })) : [];
  const details = it ? (it.details || []).map((t) => ({ t })) : [];
  const after = (r) => { if (r && r.id && r.id !== st.tdItem) app.setState({ tdItem: r.id }); };
  const rename = (e) => {
    const t = (e.target.value || '').trim().replace(/\s+/g, ' ');
    if (!it) return;
    if (!t) { e.target.value = it.title; return; }
    const was = it.id;  // an undo gives the item its old name, and with it its old id
    const box = e.target, old = it.title;
    if (t !== it.title) send(app, { rename: it.id, title: t }, null, () => app.setState({ tdItem: was })).then((r) => { if (r) after(r); else box.value = old; });
  };
  const renameKey = (e) => {
    if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); e.target.blur(); }
    else if (e.key === 'Escape' && it) { e.target.value = it.title; e.target.blur(); }
  };
  const blocks = (d && d.blocks) || [];
  const planRows = [];
  if (it && it.planned) planRows.push({ a: 'Unplan', b: planWords(it.planned) + ' · ' + it.planned.title, pick: () => { app.setState({ sheet: null }); send(app, { unplan: it.id }).then(after); } });
  for (const b of blocks.filter((x) => !x.past)) {
    planRows.push({ a: b.title, b: blockWhen(b) + (it && it.planned && it.planned.id === b.id ? ' · now' : ''), pick: () => { app.setState({ sheet: null }); if (it) send(app, { plan: it.id, block: b.id }).then(after); } });
  }
  if (!planRows.length) planRows.push({ a: 'No blocks in the calendar in the next two weeks', b: '', pick: () => app.setState({ sheet: null }) });
  const rep = (it && it.repeats) || '';
  const repRows = REPEATS.filter((r) => !(rep && r[0] === rep)).map((r) => ({ a: r[1], b: (r[0] === 'off' && !rep) ? 'Chosen' : '', pick: () => { app.setState({ sheet: null }); if (it) send(app, { repeat: it.id, rule: r[0] }).then(after); } }));
  if (rep) repRows.unshift({ a: rep[0].toUpperCase() + rep.slice(1), b: 'Chosen', pick: () => app.setState({ sheet: null }) });
  const moveRows = listsOf(d).filter((x) => (!il || x.key !== il.key) && !['done', 'letgo', 'grocoff'].includes(x.kind)).map((x) => ({
    a: x.name, b: '',
    pick: () => { app.setState({ sheet: null }); if (it) send(app, { move: it.id, to: x.key }).then((r) => { if (r) app.setState({ tdList: x.key, tdItem: r.id || it.id }); }); }
  }));
  // The overview's add box: HQ adds into a named list, so Enter asks which one first.
  const pickRows = listsOf(d).filter((x) => !['done', 'letgo', 'grocoff'].includes(x.kind)).map((x) => ({
    a: x.name, b: '', pick: () => { const t = app.state.tdPending; app.setState({ sheet: null, tdPending: '' }); if (t) send(app, { add: t, list: x.key }); }
  }));
  const sheets = {
    pickList: { title: 'Which list?', rows: pickRows },
    plan: { title: 'Plan it in a block', rows: planRows },
    repeat: { title: 'Comes back', rows: repRows },
    move: { title: iClosed ? 'Back on a list' : 'Move to another list', rows: moveRows }
  };

  // Groceries: in the list's own order; ticked off A to Z, and a tap puts one back
  const gItems = groceriesL ? groceriesL.items : [];
  const groceries = gItems.map((g) => Object.assign({ id: g.id, name: g.title, toggle: () => send(app, { tick: g.id }, (x) => without(x, g.id)) }, tick(false)));
  const tItems = tickedL ? tickedL.items.slice().sort((a, b) => a.title.localeCompare(b.title, undefined, { sensitivity: 'base' })) : [];
  const groTicked = tItems.map((g) => ({ id: g.id, name: g.title, when: g.at ? 'Last bought ' + shortDate(g.at) : '', back: () => send(app, { untick: g.id }, (x) => without(x, g.id)) }));
  const addGro = (text) => send(app, { add: text, list: groceriesL ? groceriesL.key : 'groceries' });

  const rows = { todo: ['To-do', d ? openCount + ' open' : (loading ? '…' : ''), 'todo'] };
  const homeLines = d ? { todo: { t: openCount === 1 ? '1 to-do open' : openCount + ' to-dos open', c: '#0f172a', w: '400' } } : {};
  const listTitle = st.listKind === 'done' ? 'Done' : st.listKind === 'letgo' ? 'Let go' : (l ? l.name : 'To-do');

  return {
    agent: { donna: { rows, homeLines } },
    sheets,
    titles: { todoList: listTitle },
    submit: { todoGro: addGro, todoOverview: (text) => { if (!d) return; app.setState({ tdPending: text, sheet: 'pickList' }); } },
    values: {
      boxes, item, itemDeco: 'none', tickLabel: 'Tick it off',
      tickItem: () => { if (!it) return; send(app, iGro ? { tick: it.id } : { done: it.id }, (x) => without(x, it.id)); app.back(); },
      letGo: () => { if (!it) return; send(app, { letgo: it.id, why: '' }, (x) => without(x, it.id)); app.back(); },
      todoRows, todoFilters, listClosed: closed, listOpen: !!l && !closed,
      openDone: () => app.go('todoList', { listKind: 'done', tdList: doneL ? doneL.key : null }),
      openLetgo: () => app.go('todoList', { listKind: 'letgo', tdList: letgoL ? letgoL.key : null }),
      plannedText: it && it.planned ? planWords(it.planned) + ' · ' + it.planned.title : 'Not planned',
      itemDead: (it && it.deadline) || 'None', itemDeadC: it && it.deadline && soon(it.deadline) ? '#b42318' : '#0f172a',
      repeatText: rep ? 'Repeats ' + rep : 'Doesn’t repeat',
      sheetPlan: () => app.setState({ sheet: 'plan' }), sheetRepeat: () => app.setState({ sheet: 'repeat' }), sheetMove: () => app.setState({ sheet: 'move' }),
      groceries, groTicked,
      todoX: {
        loading, failed: !d && !off && !!st.tdErr, retry,
        hasCommit: commit.length > 0, commitName: commit.map((x) => x.name).join(' + '),
        commitLine: cItems.length ? cItems.slice(0, 3).map((x) => x.title).join(' · ') + (cItems.length > 3 ? ' …' : '') : 'Nothing promised right now',
        openCommit: commit.length ? openList(commit[0].key) : () => {},
        empty: off || empty, full: !!d && !empty,
        nGroceries: groceriesL ? groceriesL.items.length : '', nDone: doneL ? doneL.items.length : '', nLetGo: letgoL ? letgoL.items.length : '',
        listNote, hasRows: todoRows.length > 0, sortable,
        addDraft: st.tdAdd, addInput, addKey,
        itemHere: !!it, itemGone: !!d && !it, plainTitle: false, renamable: !!it, nameValue: it ? it.title : '', rename, renameKey,
        forWho: (it && it.for) || 'You',
        canPlan: !!it && !iClosed && !iGro, canRepeat: !!it && !iClosed && !iGro, canTick: !!it && !iClosed && il.kind !== 'grocoff',
        canLetGo: !!it && !iClosed && !!letgoL, moveLabel: iClosed ? 'Back on a list' : 'Move to a list',
        fields, details,
        groNote: !d ? (loading ? 'Getting your groceries…' : 'Your groceries didn’t load.') : (gItems.length ? '' : 'Nothing on the groceries right now.'),
        hasGroceries: gItems.length > 0, hasGroTicked: tItems.length > 0,
        groTickedNote: d && !tItems.length ? 'What you tick off lands here, A to Z. Tap one to put it back on the list.' : ''
      }
    }
  };
}

// The prototypes' made-up content, as the design shows it (demo mode).
function demoVals(st, ctx, D) {
  const { app } = ctx;
  const go = (k, extra) => () => app.go(k, extra);
  const say = (t) => app.say(t);
  const openItem = (box, title) => go('todoItem', { item: { box, title }, itemDone: false, planned: null, repeat: 'Doesn’t repeat' });
  const boxes = D.boxCards.map((b) => Object.assign({}, b, {
    openAll: go('todoList', { todoBox: b.name, listKind: 'box', todoFilter: 'all' }),
    more: b.count > b.items.length ? '+ ' + (b.count - b.items.length) + ' more' : 'See the list',
    items: b.items.map((t) => ({ title: t, open: openItem(b.name, t) }))
  }));
  const item = st.item || D.firstItem;
  const closedL = st.listKind !== 'box';
  let src = st.listKind === 'done' ? D.done : st.listKind === 'letgo' ? D.letGo : (D.boxes[st.todoBox] || []);
  const cntAll = src.length, cntPl = src.filter((t) => D.planned[t]).length;
  if (!closedL && st.todoFilter === 'planned') src = src.filter((t) => D.planned[t]);
  if (!closedL && st.todoFilter === 'open') src = src.filter((t) => !D.planned[t]);
  const todoRows = src.map((t) => ({
    title: t,
    meta: [D.deadlines[t] ? 'Deadline ' + D.deadlines[t] : '', D.planned[t] || ''].filter(Boolean).join(' · ') || (closedL ? (st.listKind === 'done' ? 'Done this week' : 'Let go last month') : 'For you'),
    mc: D.deadlines[t] ? '#b42318' : '#475569',
    open: go('todoItem', { item: { box: st.todoBox, title: t }, itemDone: false, planned: null, repeat: 'Doesn’t repeat' }),
    tick: () => say('Ticked off “' + t + '”'), back: () => say('“' + t + '” is back on a list')
  }));
  const todoFilters = closedL ? [] : [['all', 'All', cntAll], ['planned', 'Planned', cntPl], ['open', 'Not planned', cntAll - cntPl]].map((f) => {
    const on = st.todoFilter === f[0];
    return Object.assign({ name: f[1] + ' ' + f[2], on: on ? 'true' : 'false', pick: () => app.setState({ todoFilter: f[0] }) }, chip(on));
  });
  const todoListTitle = st.listKind === 'done' ? 'Done' : st.listKind === 'letgo' ? 'Let go' : st.todoBox;
  const groceries = D.groceries.map((n) => Object.assign({ name: n, toggle: flip(app, 'bought', n) }, tick(!!st.bought[n])));
  const groTicked = D.groceriesTicked.map((g) => ({ name: g[0], when: g[1], back: () => say(g[0] + ' is back on the list') }));
  const sheets = {
    plan: { title: 'Plan it in a block', rows: D.planBlocks.map((r) => ({ a: r[0] + ' · ' + r[1], b: r[2], pick: () => { app.setState({ planned: 'Planned ' + r[0].toLowerCase() + ' ' + r[1].slice(0, 5) + ' · ' + r[2], sheet: null }); say('Planned ' + r[0].toLowerCase() + ' at ' + r[1].slice(0, 5)); } })) },
    repeat: { title: 'Comes back', rows: D.repeats.map((r) => ({ a: r, b: st.repeat === r ? 'Chosen' : '', pick: () => app.setState({ repeat: r, sheet: null }) })) },
    move: { title: 'Move to another list', rows: D.moveTo.map((r) => ({ a: r, b: '', pick: () => { app.setState({ sheet: null }); say('Moved to ' + r); } })) }
  };
  return {
    agent: { donna: { rows: D.rows, homeLines: D.homeLines } },
    sheets,
    titles: { todoList: todoListTitle },
    values: {
      boxes, item, itemDeco: st.itemDone ? 'line-through' : 'none', tickLabel: st.itemDone ? 'Back on the list' : 'Tick it off',
      tickItem: () => { app.setState((x) => ({ itemDone: !x.itemDone })); if (!st.itemDone) say('Ticked off. It’s under Done now'); },
      letGo: () => { app.back(); say('Let go. You’ll find it under Let go'); },
      todoRows, todoFilters, listClosed: closedL, listOpen: !closedL,
      openDone: go('todoList', { listKind: 'done' }), openLetgo: go('todoList', { listKind: 'letgo' }),
      plannedText: st.planned || 'Not planned', itemDead: D.deadlines[item.title] || 'None', itemDeadC: D.deadlines[item.title] ? '#b42318' : '#0f172a', repeatText: st.repeat,
      sheetPlan: () => app.setState({ sheet: 'plan' }), sheetRepeat: () => app.setState({ sheet: 'repeat' }), sheetMove: () => app.setState({ sheet: 'move' }),
      groceries, groTicked,
      // What the wired templates read beyond the prototype's values, filled from the made-up content
      todoX: {
        loading: false, failed: false, hasCommit: true, commitName: 'Commitments to others', commitLine: 'Send Alex the photos · Call the plumber back',
        empty: !!st.fresh, full: !st.fresh, nGroceries: D.groceries.length, nDone: D.done.length, nLetGo: D.letGo.length,
        listNote: '', hasRows: true, sortable: !closedL,
        itemHere: true, itemGone: false, plainTitle: true, renamable: false, forWho: 'You',
        canPlan: true, canRepeat: true, canTick: true, canLetGo: true, moveLabel: 'Move to a list', fields: [], details: [],
        groNote: '', hasGroceries: true, hasGroTicked: true, groTickedNote: ''
      }
    }
  };
}
