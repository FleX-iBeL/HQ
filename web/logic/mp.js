// Moneypenny's area: hand-overs, status, the planning board, work sessions, health, updates.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/mp.js';

export const NAME = 'mp';
export const WIRED = false;
export { demo };

export const start = { updating: 0 };

export const card = (st, D) => D.card;

export function vals(st, ctx, D) {
  const { app } = ctx;
  return {
    agent: { mp: { homeLines: D.homeLines, rows: D.rows } },
    sheets: {},
    titles: {},
    values: {
      handovers: D.handovers.map((h) => Object.assign({}, h, { open: () => app.go('handover') })),
      working: D.working, planning: D.planning, sessionRows: D.sessions, routines: D.routines,
      updLabel: D.update.labels[st.updating], updIdle: st.updating === 0, updBusy: st.updating === 1, updDone: st.updating === 2,
      startUpdate: () => { app.setState({ updating: 1 }); setTimeout(() => app.setState({ updating: 2 }), D.update.takesMs); },
      reload: () => { app.setState({ updating: 0 }); app.say(D.update.doneSay); }
    }
  };
}
