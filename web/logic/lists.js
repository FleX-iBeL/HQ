// The lists area (Donna): the lists screen's tabs, the bucketlist and the wishlist, a bucket
// item with its sub-items, price, goal, score and links, and the add boxes. (The groceries
// tab's content is the to-do area's.)
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/lists.js';
import { chip, flip, tick } from './util.js';

export const NAME = 'lists';
export const WIRED = false;
export { demo };

export const start = { listTab: 'groceries', subsDone: { flights: true }, bDel: false, score: 5, period: 'once', links: demo.links.slice(), bucketId: null, added: { bucket: [], wish: [] } };

export function vals(st, ctx, D) {
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
  return {
    agent: { donna: { rows: D.rows } },
    submit: { bucket: add('bucket'), wish: add('wish') },
    titles: { bucketItem: D.titles.bucketItem, subItem: D.titles.subItem },
    values: {
      lists, listTabs, lt, bucket, wish, subs,
      periodChips, scoreBtns, linkRows, delTap, delLabel: st.bDel ? 'Tap again to delete' : 'Delete', delBg: st.bDel ? '#d9392b' : '#ffffff', delFg: st.bDel ? '#ffffff' : '#b42318',
      openSub: go('subItem')
    }
  };
}
