// Pepper's area: the map and its layers, check-ins, the games.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/pepper.js';

export const NAME = 'pepper';
export const WIRED = false;
export { demo };

export const start = { walk: true, pages: demo.pages, feel: null, kept: false, gameId: demo.currentGame };

export const card = (st, D) => D.card;

const GRID = { done: ['#c2410c', '#ffffff', 'none'], x: ['#f1f5f9', '#94a3b8', 'none'], none: ['#f8fafc', '#cbd5e1', 'none'], today: ['#ffffff', '#0f172a', '0 0 0 2px #0f172a inset'], future: ['#f8fafc', '#cbd5e1', 'none'] };

export function vals(st, ctx, D) {
  const { app } = ctx;
  const layers = D.layers.map((l) => ({ name: l[0], st: l[1], pct: l[2], open: () => app.go('layer') }));
  const grid = D.marks.map((m, i) => {
    if (m === 'today') m = st.walk ? 'done' : 'today';
    const v = GRID[m] || GRID.none;
    return { d: D.days[i], bg: v[0], fg: v[1], ring: i === D.todayIndex ? '0 0 0 2px #0f172a inset' : v[2] };
  });
  const checklist = D.checklist.map((c) => ({ q: c[0], mark: c[1], mc: c[2], note: c[3], hasNote: !!c[3] }));
  const feelChips = D.feelings.map((f) => {
    const on = st.feel === f;
    return { name: f, pick: () => app.setState({ feel: f }), bg: on ? '#c2410c' : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });
  return {
    agent: { pepper: { homeLines: D.homeLines, rows: D.rows } },
    sheets: {},
    titles: { layer: D.layerTitle },
    values: {
      layers, grid, checklist, feelChips,
      // gameId says which game is open; the demo shows the current game's content for every one
      pastGames: D.pastGames.map((g) => Object.assign({}, g, { open: () => app.go('game', { gameId: g.id }) })),
      walkToggle: () => app.setState((x) => ({ walk: !x.walk })), walkLabel: st.walk ? 'Done' : 'Not yet', walkBg: st.walk ? '#c2410c' : '#f1f5f9', walkFg: st.walk ? '#ffffff' : '#0f172a',
      pages: st.pages, pagesUp: () => app.setState((x) => ({ pages: x.pages + 1 })), pagesDown: () => app.setState((x) => ({ pages: Math.max(0, x.pages - 1) })),
      openGame: () => app.go('game', { gameId: D.currentGame }),
      kept: st.kept, notKept: !st.kept, keepIt: () => { app.setState({ kept: true }); app.say('Kept. Pepper reads it at the check-in'); }
    }
  };
}
