// The inbox area (Donna): mail on home, his quick notes, her notes (in each of the three
// spaces), her nudges, what she keeps an eye out for, cleared notes.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/inbox.js';
import { flip } from './util.js';

export const NAME = 'inbox';
export const WIRED = false;
export { demo };

export const start = { nudges: { passport: false, fine: false }, nbell: { passport: true, fine: true }, clearedOpen: false };

export function vals(st, ctx, D) {
  const { app } = ctx;
  const nudges = D.nudges.map((n) => {
    const isDone = st.nudges[n.id];
    return { title: n.title, sub: isDone ? 'Done · she stopped nudging' : n.sub, label: isDone ? 'Undo' : 'Done',
      deco: isDone ? 'line-through' : 'none', fc: isDone ? '#94a3b8' : '#0f172a', toggle: flip(app, 'nudges', n.id) };
  });
  const nudgeCount = D.nudges.filter((n) => !st.nudges[n.id]).length;
  const allDone = D.nudges.every((n) => st.nudges[n.id]);
  const nudgeRows = D.nudgeNotes.map((n) => {
    const on = st.nbell[n[0]]; const isDone = st.nudges[n[0]];
    return { t: n[1], when: isDone ? 'Done' : 'Nudging you ' + n[2], bell: flip(app, 'nbell', n[0]),
      bellBg: on ? '#f5f3ff' : '#f1f5f9', bellFg: on ? '#6d28d9' : '#94a3b8', bellAria: on ? 'Stop the texts for this nudge' : 'Text me for this nudge',
      done: flip(app, 'nudges', n[0]), doneLabel: isDone ? 'Undo' : 'Done' };
  });
  return {
    agent: { donna: { rows: D.rows, homeLines: Object.assign({ nudges: { t: allDone ? D.nudgeLines.none : D.nudgeLines.left, c: '#0f172a', w: '400' } }, D.homeLines) } },
    values: {
      nudges, nudgeCount, nudgeRows,
      myNotes: D.myNotes, herNotes: D.notesBy[st.space], isDonnaNotes: st.space === 'donna',
      eyeRows: D.eyeRows, clearedRows: D.clearedRows, clearedOpen: st.clearedOpen,
      toggleCleared: () => app.setState((x) => ({ clearedOpen: !x.clearedOpen })), clearedLabel: st.clearedOpen ? 'Hide cleared notes' : 'Show cleared notes (' + D.clearedRows.length + ')'
    }
  };
}
