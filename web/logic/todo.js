// The to-do area (Donna): the four boxes, the full list behind a box, an item (plan it in,
// comes back, move, let go, tick off), the done and let-go lists, the undo line, groceries
// and ticked-off groceries (the groceries tab of the lists screen).
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/todo.js';
import { chip, flip, tick } from './util.js';

export const NAME = 'todo';
export const WIRED = false;
export { demo };

export const start = { item: null, itemDone: false, bought: {}, todoBox: 'Important, not urgent', listKind: 'box', todoFilter: 'all', planned: null, repeat: 'Doesn’t repeat' };

export function vals(st, ctx, D) {
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
      groceries, groTicked
    }
  };
}
