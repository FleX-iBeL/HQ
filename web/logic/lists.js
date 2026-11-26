// The lists area (Donna): the lists screen's tabs, the bucketlist and the wishlist with their
// totals, an item's page (every field, its links, sub-items inside sub-items with the path
// above it), the add boxes, done and let go, move up and down, delete. (The groceries tab's
// content is the to-do area's.)
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data
// (GET api/lists as the server gives it; changes go to POST api/lists with x-hq: lists).
import * as demo from './demo/lists.js';
import { chip, flip, tick } from './util.js';

export const NAME = 'lists';
export const WIRED = true;
export const LOADING_OK = true;
export { demo };

// bucketList and bucketPath: which list and which item is open, as the ids from the main item
// down (bucketId is the last one); lErr: the first load failed; lClosed: the done and let-go
// ones unfolded; lOwn: per item with sub-items, whether its own details are unfolded.
export const start = { listTab: 'groceries', subsDone: { flights: true }, bDel: false, score: 5, period: 'once', links: demo.links.slice(), bucketId: null, added: { bucket: [], wish: [] },
  bucketList: 'bucket', bucketPath: [], lErr: false, lClosed: false, lOwn: {} };

const ITEM_SCREENS = ['bucketItem', 'subItem'];
const KIND_NAMES = { experience: 'Experience', product: 'Product', service: 'Service' };

// ---- talking to the server -------------------------------------------------------------

export async function load(app) {
  try {
    const d = await app.api.get('api/lists');
    app.setData('lists', d);
    if (app.state.lErr) app.setState({ lErr: false });
  } catch (err) {
    if (!app.state.data.lists) app.setState({ lErr: true });
    throw err;
  }
}

export const enter = { lists: (app) => load(app), todo: (app) => load(app), donna: (app) => load(app) };

// A change: shown at once (patch), then the lists as the server has them, with the words it
// said and its Undo. A refusal puts the server's lists back and says why.
async function send(app, body, patch) {
  if (patch) app.setData('lists', (d) => (d && Array.isArray(d.lists) ? patch(JSON.parse(JSON.stringify(d))) || d : d));
  try {
    const d = await app.api.post('api/lists', body, 'lists');
    if (d && Array.isArray(d.lists)) app.setData('lists', d);
    const undo = d && d.undo ? () => send(app, { do: 'undo' }) : null;
    if (d && d.said) app.say(d.said, undo);
    return d;
  } catch (err) {
    app.say(err && err.status === 0 ? 'Couldn’t reach HQ. Try again.' : ((err && err.message) || 'Couldn’t change the list. Try again.'));
    load(app).catch(() => {});
    return null;
  }
}

// ---- reading the real data -------------------------------------------------------------

const listOf = (d, key) => ((d && d.lists) || []).find((l) => l.key === key) || null;
// The items along a path of ids, from the main item down (null when one is gone).
function trail(d, key, path) {
  const out = []; let items = (listOf(d, key) || { items: [] }).items;
  for (const id of path) { const it = items.find((x) => x.id === id); if (!it) return null; out.push(it); items = it.sub || []; }
  return out;
}
function findIn(items, id) {
  for (const it of items) { if (it.id === id) return it; const s = findIn(it.sub || [], id); if (s) return s; }
  return null;
}
function patchItem(d, key, id, fn) { const l = listOf(d, key); const it = l && findIn(l.items, id); if (it) fn(it); return d; }

const num = (n) => Number(n).toLocaleString('en-US', { maximumFractionDigits: 2 });
function money(t) {
  const p = [];
  if (t.once) p.push('€' + num(t.once));
  if (t.month) p.push('€' + num(t.month) + ' a month');
  if (t.year) p.push('€' + num(t.year) + ' a year');
  return p.join(' + ');
}
function metaOf(it) {
  const t = it.totals || {}, p = [money(t)];
  if (t.hours) p.push(num(t.hours) + ' h');
  if (it.by) p.push('by ' + it.by);
  if (t.subs) p.push(t.subs_done + ' of ' + t.subs + ' done');
  if (it.score) p.push('score ' + it.score + ' of 5');
  if ((it.links || []).length) p.push(it.links.length === 1 ? '1 link' : it.links.length + ' links');
  if (it.notes) p.push('notes');
  if (it.state === 'done') p.push('done'); else if (it.state === 'dropped') p.push('let go');
  return p.filter(Boolean).join(' · ') || (it.state === 'open' ? 'Tap to give it a price, a goal, links, notes' : '');
}
// The totals card: the money once, a month, a year, what's still to spend, the hours, how many done.
function cells(t, withDone) {
  const c = [];
  if (t.once) c.push({ v: '€' + num(t.once), l: 'once' });
  if (t.month) c.push({ v: '€' + num(t.month), l: 'a month' });
  if (t.year) c.push({ v: '€' + num(t.year), l: 'a year' });
  if (!c.length) c.push({ v: '€0', l: 'no prices yet' });
  if (t.left && t.left !== t.once) c.push({ v: '€' + num(t.left), l: 'still to spend' });
  if (t.hours) c.push({ v: num(t.hours) + ' h', l: 'time' });
  if (withDone && t.subs) c.push({ v: t.subs_done + ' of ' + t.subs, l: 'done' });
  return c;
}
// How deep the open item is: one per item screen at the end of the way back.
function depthOf(st) {
  let n = ITEM_SCREENS.includes(st.screen) ? 1 : 0;
  for (let i = st.stack.length - 1; i >= 0 && ITEM_SCREENS.includes(st.stack[i]); i--) n++;
  return Math.max(1, n);
}

// ---- the values ------------------------------------------------------------------------

export function vals(st, ctx, D) {
  return D === demo ? demoVals(st, ctx, D) : realVals(st, ctx, D);
}

function realVals(st, ctx, D) {
  const { app } = ctx;
  const go = (k, extra) => () => app.go(k, extra);
  const d = D && Array.isArray(D.lists) ? D : null;
  const off = !!(D && D.off);
  const failed = !d && !off && !!st.lErr;
  const loading = !d && !off && !st.lErr;
  const lists = { groceries: go('lists', { listTab: 'groceries' }), bucket: go('lists', { listTab: 'bucket' }), wish: go('lists', { listTab: 'wish' }) };
  const listTabs = [['groceries', 'Groceries'], ['bucket', 'Bucketlist'], ['wish', 'Wishlist']].map((t) => {
    const on = st.listTab === t[0];
    return { name: t[1], on: on ? 'true' : 'false', pick: () => app.setState({ listTab: t[0] }), bg: on ? '#0f172a' : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });
  const lt = { groceries: st.listTab === 'groceries', bucket: st.listTab === 'bucket', wish: st.listTab === 'wish' };
  const retry = () => { app.setState({ lErr: false }); load(app).catch(() => {}); };
  const openMain = (key, it) => go('bucketItem', { bucketList: key, bucketPath: [it.id], bucketId: it.id, bDel: false });
  // A row: tap to open; its tick circle marks it done, or open again (a let-go one ticked is done).
  const tickRow = (key, it) => (e) => {
    if (e && e.stopPropagation) e.stopPropagation();
    const to = it.state === 'done' ? 'open' : 'done';
    send(app, { do: to, item: it.id }, (x) => patchItem(x, key, it.id, (y) => { y.state = to; }));
  };
  const rowOf = (key) => (it) => {
    const open = openMain(key, it);
    return Object.assign({ id: it.id, name: it.name, meta: metaOf(it), open, toggle: tickRow(key, it), tickAria: it.state === 'done' ? 'Open ' + it.name + ' again' : 'Tick off ' + it.name,
      key: (e) => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); open(); } } }, tick(it.state === 'done'));
  };
  const B = listOf(d, 'bucket'), W = listOf(d, 'wish');
  const part = (l) => {
    const items = l ? l.items : [];
    return { open: items.filter((x) => x.state === 'open'), closed: items.filter((x) => x.state !== 'open') };
  };
  const bp = part(B), wp = part(W);
  const fold = (n) => (n ? (st.lClosed ? 'Hide done or let go · ' : 'Done or let go · ') + n : '');
  const add = (key) => (text) => send(app, { do: 'add', name: text, list: key });

  // One item: the path from the main item down to the one that's open
  const depth = depthOf(st);
  const path = (st.bucketPath || []).slice(0, depth);
  const key = st.bucketList || 'bucket', L = listOf(d, key);
  const chain = d && path.length ? trail(d, key, path) : null;
  const it = chain ? chain[chain.length - 1] : null;
  const subsAll = it ? it.sub || [] : [];
  const subsOpen = subsAll.filter((x) => x.state === 'open'), subsClosed = subsAll.filter((x) => x.state !== 'open');
  const subsShown = subsOpen.concat(st.lClosed ? subsClosed : []);
  const set = (field, value) => it && send(app, { do: 'set', item: it.id, field, value: String(value) }, (x) => patchItem(x, key, it.id, (y) => { y[field] = value; }));
  const save = {};
  for (const f of ['name', 'price', 'by', 'hours', 'why', 'notes']) {
    save[f] = (e) => {
      if (!it) return;
      const v = (e.target.value || '').trim(), was = it[f] == null ? '' : String(it[f]);
      if (v === was || (f === 'price' && v.replace(/[€\s]/g, '') === was)) return;
      if (f === 'name' && !v) { e.target.value = it.name; return; }
      const box = e.target;  // a refused value goes back to what's kept, the reason in the toast
      send(app, { do: 'set', item: it.id, field: f, value: v }).then((r) => { if (!r) box.value = was; });
    };
  }
  const has = !!it && !!(it.kind || it.price || it.by || it.hours || it.score || (it.links || []).length || it.notes);
  const ownOpen = !it || !subsAll.length || (it.id in st.lOwn ? st.lOwn[it.id] : has);
  const kindChips = (d && d.kinds ? d.kinds : Object.keys(KIND_NAMES)).map((k) => {
    const on = !!it && it.kind === k;
    return Object.assign({ name: KIND_NAMES[k] || k, on: on ? 'true' : 'false', pick: () => set('kind', on ? '' : k) }, chip(on));
  });
  const periodChips = [['once', 'Once'], ['month', 'A month'], ['year', 'A year']].map((p) => Object.assign({ name: p[1], pick: () => set('every', p[0]) }, chip(!!it && (it.every || 'once') === p[0])));
  const scoreBtns = [1, 2, 3, 4, 5].map((n) => { const on = !!it && it.score === n; return { n, pick: () => set('score', on ? '' : n), bg: on ? '#0f172a' : '#ffffff', fg: on ? '#ffffff' : '#0f172a' }; });
  const linkRows = (it ? it.links || [] : []).map((u, i) => ({ t: u.replace(/^https?:\/\/(www\.)?/, ''), href: u, remove: () => send(app, { do: 'unlink', item: it.id, url: String(i + 1) }) }));
  const subs = subsShown.map((s) => Object.assign({ id: s.id, name: s.name, meta: metaOf(s), toggle: () => send(app, { do: s.state === 'open' ? 'done' : 'open', item: s.id }, (x) => patchItem(x, key, s.id, (y) => { y.state = y.state === 'open' ? 'done' : 'open'; })) }, tick(s.state !== 'open')));
  const openSub = (e) => {
    const id = e && e.currentTarget && e.currentTarget.dataset ? e.currentTarget.dataset.id : '';
    if (!id || !it) return;
    app.go('bucketItem', { bucketList: key, bucketPath: path.concat(id), bucketId: id, bDel: false });
  };
  const armed = !!it && st.bDel === it.id;
  const delTap = () => {
    if (!it) return;
    if (!armed) { app.setState({ bDel: it.id }); clearTimeout(app._ld); app._ld = setTimeout(() => app.setState((x) => (x.bDel === it.id ? { bDel: false } : null)), 5000); return; }
    app.setState({ bDel: false });
    app.back();
    send(app, { do: 'delete', item: it.id });
  };
  const crumb = L && chain ? [L.name].concat(chain.map((x) => x.name)).join(' › ') : '';
  const itemGone = d && !it ? (path.length ? 'This one isn’t on the list anymore.' : 'Pick something on the list to open it.') : (loading ? 'Getting your lists…' : (failed ? 'Your lists didn’t load.' : ''));
  const f = it ? { name: it.name, price: it.price == null ? '' : String(it.price), by: it.by || '', hours: it.hours == null ? '' : String(it.hours), why: it.why || '', notes: it.notes || '' } : {};

  // The sub-item screen: the open item as a short read-only summary (nothing in HQ opens it; every
  // item and sub-item opens its full page)
  const sub = it ? {
    crumb, open: go('bucketItem', { bucketList: key, bucketPath: path, bucketId: it.id }),
    rows: [['Kind', KIND_NAMES[it.kind] || '—'], ['Price', it.price ? '€' + num(it.price) + ' ' + ({ month: 'a month', year: 'a year' }[it.every] || 'once') : '—'], ['Goal', it.by || '—'],
      ['Score', it.score ? it.score + ' of 5' : '—', '700'], ['Notes', it.notes || '—']].map((r) => ({ k: r[0], v: r[1], w: r[2] || '400' })),
    under: subsAll.length ? subsAll.length + ' under it · open it to change anything' : 'Nothing under it yet · open it to add something'
  } : { crumb: '', rows: [], under: '', open: () => {} };

  const nB = B ? B.open : '', nW = W ? W.open : '';
  const rows = { lists: ['Lists', d ? nB + ' bucket · ' + nW + ' wish' : (loading ? '…' : ''), 'lists'] };
  const gro = st.data && st.data.todo && Array.isArray(st.data.todo.lists) ? st.data.todo.lists.find((x) => x.kind === 'groceries') : null;
  if (gro && d) rows.lists[1] = gro.items.length + ' groceries · ' + rows.lists[1];

  return {
    agent: { donna: { rows } },
    submit: {
      bucket: add('bucket'), wish: add('wish'),
      listSub: (text) => it && send(app, { do: 'add', name: text, under: it.id }),
      listLink: (text) => it && send(app, { do: 'link', item: it.id, url: text })
    },
    titles: { bucketItem: it ? it.name : (L ? L.name : 'Lists'), subItem: it ? it.name : 'Lists' },
    values: {
      lists, listTabs, lt,
      bucket: bp.open.map(rowOf('bucket')), wish: wp.open.map(rowOf('wish')), subs,
      periodChips, scoreBtns, linkRows, delTap, delLabel: armed ? 'Tap again to delete' : 'Delete', delBg: armed ? '#d9392b' : '#ffffff', delFg: armed ? '#ffffff' : '#b42318',
      openSub,
      listX: {
        note: loading ? 'Getting your lists…' : (failed ? 'Your lists didn’t load.' : (off ? 'Free is on: none of your files.' : '')), failed, retry,
        nBucket: nB, nWish: nW,
        bucketTotalsOn: !!B, bucketTotals: B ? cells(B.totals || {}, true) : [], bucketEmpty: !!B && !B.items.length, bucketHasOpen: bp.open.length > 0,
        bucketFold: fold(bp.closed.length), bucketHasClosed: bp.closed.length > 0, bucketClosed: bp.closed.map(rowOf('bucket')),
        wishTotalsOn: !!W, wishTotals: W ? cells(W.totals || {}, true) : [], wishEmpty: !!W && !W.items.length, wishHasOpen: wp.open.length > 0,
        wishFold: fold(wp.closed.length), wishHasClosed: wp.closed.length > 0, wishClosed: wp.closed.map(rowOf('wish')),
        wishOpens: true, wishCursor: 'pointer',
        closedOpen: !!st.lClosed, closedOpenAria: st.lClosed ? 'true' : 'false', toggleClosed: () => app.setState((x) => ({ lClosed: !x.lClosed })),
        itemHere: !!it, itemGone, crumb, renamable: !!it, f, save,
        blurOnEnter: (e) => { if (e.key === 'Enter' && !e.isComposing) { e.preventDefault(); e.target.blur(); } },
        hasSubs: subsAll.length > 0, itemTotals: it ? cells(it.totals || {}, true) : [],
        subFold: subsClosed.length ? fold(subsClosed.length) : '', subAddPlain: false, subAddBox: !!it,
        ownFold: it && subsAll.length ? (ownOpen ? 'Hide this item’s own price, goal, links and notes' : 'This item’s own price, goal, links and notes') : '',
        ownOpen, ownOpenAria: ownOpen ? 'true' : 'false',
        toggleOwn: () => it && app.setState((x) => ({ lOwn: Object.assign({}, x.lOwn, { [it.id]: !ownOpen }) })),
        kindChips,
        doneLabel: it && it.state !== 'open' ? 'Open again' : 'Done',
        doneTap: () => it && send(app, { do: it.state === 'open' ? 'done' : 'open', item: it.id }),
        canLetGo: !!it && it.state !== 'dropped', letGoTap: () => it && send(app, { do: 'drop', item: it.id }),
        canMove: !!it, moveUp: () => it && send(app, { do: 'move', item: it.id, to: 'up' }), moveDown: () => it && send(app, { do: 'move', item: it.id, to: 'down' }),
        sub
      }
    }
  };
}

// The prototypes' made-up content, as the design shows it (demo mode).
function demoVals(st, ctx, D) {
  const { app } = ctx;
  const go = (k, extra) => () => app.go(k, extra);
  const say = (t) => app.say(t);
  const lists = { groceries: go('lists', { listTab: 'groceries' }), bucket: go('lists', { listTab: 'bucket' }), wish: go('lists', { listTab: 'wish' }) };
  const listTabs = [['groceries', 'Groceries'], ['bucket', 'Bucketlist'], ['wish', 'Wishlist']].map((t) => {
    const on = st.listTab === t[0];
    return { name: t[1], on: on ? 'true' : 'false', pick: () => app.setState({ listTab: t[0] }), bg: on ? '#0f172a' : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });
  const lt = { groceries: st.listTab === 'groceries', bucket: st.listTab === 'bucket', wish: st.listTab === 'wish' };
  // bucketId says which item is open; the demo shows the same example item for every one
  const bucket = D.bucket.concat(st.added.bucket).map((b) => Object.assign({}, b, { open: go('bucketItem', { bucketId: b.id }) }));
  const wish = D.wish.concat(st.added.wish);
  const add = (list) => (text) => {
    app.setState((x) => ({ added: Object.assign({}, x.added, { [list]: x.added[list].concat([{ id: list + '-' + Date.now(), name: text, meta: D.newMeta[list] }]) }) }));
    say(list === 'bucket' ? 'Added to your bucketlist' : 'Added to your wishlist');
  };
  const subs = D.subItems.map((x) => Object.assign({ name: x[1], meta: x[2] + (st.subsDone[x[0]] ? ' · done' : ''), toggle: flip(app, 'subsDone', x[0]) }, tick(!!st.subsDone[x[0]])));
  const periodChips = [['once', 'Once'], ['month', 'A month'], ['year', 'A year']].map((p) => Object.assign({ name: p[1], pick: () => app.setState({ period: p[0] }) }, chip(st.period === p[0])));
  const scoreBtns = [1, 2, 3, 4, 5].map((n) => { const on = st.score === n; return { n, pick: () => app.setState({ score: n }), bg: on ? '#0f172a' : '#ffffff', fg: on ? '#ffffff' : '#0f172a' }; });
  const linkRows = st.links.map((l, i) => ({ t: l, remove: () => app.setState((x) => ({ links: x.links.filter((_, j) => j !== i) })) }));
  const delTap = () => {
    if (st.bDel) { app.setState({ bDel: false }); app.back(); say('Deleted, with everything under it'); }
    else { app.setState({ bDel: true }); clearTimeout(app._d); app._d = setTimeout(() => app.setState({ bDel: false }), 5000); }
  };
  const kind = (on) => chip(on);
  return {
    agent: { donna: { rows: D.rows } },
    submit: { bucket: add('bucket'), wish: add('wish') },
    titles: { bucketItem: D.titles.bucketItem, subItem: D.titles.subItem },
    values: {
      lists, listTabs, lt, bucket, wish, subs,
      periodChips, scoreBtns, linkRows, delTap, delLabel: st.bDel ? 'Tap again to delete' : 'Delete', delBg: st.bDel ? '#d9392b' : '#ffffff', delFg: st.bDel ? '#ffffff' : '#b42318',
      openSub: go('subItem'),
      // What the wired templates read beyond the prototype's values, filled from the made-up content
      listX: {
        note: '', failed: false, nBucket: D.bucket.length, nWish: D.wish.length,
        bucketTotalsOn: true, bucketTotals: [{ v: '€4,070', l: 'once' }, { v: '160 h', l: 'time' }, { v: '1 of 5', l: 'done' }], bucketEmpty: false, bucketHasOpen: true,
        bucketFold: '', bucketHasClosed: false, bucketClosed: [],
        wishTotalsOn: false, wishTotals: [], wishEmpty: false, wishHasOpen: true, wishFold: '', wishHasClosed: false, wishClosed: [], wishOpens: false, wishCursor: 'default',
        closedOpen: false,
        itemHere: true, itemGone: '', crumb: 'Bucketlist › ' + D.titles.bucketItem, renamable: false,
        f: { price: '€3,020', by: 'Spring 2027', hours: '120 hours', why: 'Slow travel, new food', notes: '' }, save: {},
        hasSubs: true, itemTotals: [{ v: '€3,020', l: 'once' }, { v: '€1,620', l: 'still to spend' }, { v: '1 of 3', l: 'done' }],
        subFold: '', subAddPlain: true, subAddBox: false, ownFold: '', ownOpen: true,
        kindChips: [['Experience', true], ['Product', false], ['Service', false]].map((k) => Object.assign({ name: k[0], on: k[1] ? 'true' : 'false' }, kind(k[1]))),
        doneLabel: 'Done', canLetGo: true, canMove: false,
        sub: {
          crumb: 'Bucketlist › ' + D.titles.bucketItem + ' › ' + D.titles.subItem,
          rows: [['Kind', 'Experience'], ['Price', '€1,200 once'], ['Goal', 'Spring 2027'], ['Score', '4 of 5', '700'], ['Notes', 'The one in the mountains']].map((r) => ({ k: r[0], v: r[1], w: r[2] || '400' })),
          under: 'Nothing under it yet · + Add something under it'
        }
      }
    }
  };
}
