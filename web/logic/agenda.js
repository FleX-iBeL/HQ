// The agenda area (Donna): today across the three, the agenda, an appointment, travel,
// the kinds of time, the calendar filter. Also Donna's card (her next appointment).
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/agenda.js';
import { chip, flip } from './util.js';

export const NAME = 'agenda';
export const WIRED = false;
export { demo };

export const start = { apptMark: null, bell: true, appt: null, travel: 'bike', apptNotes: demo.apptNotes.slice(), cal: { personal: true, work: true, birthdays: true } };

export const card = (st, D) => D.card;

export function vals(st, ctx, D) {
  const { app, AG } = ctx;
  const go = (k, extra) => () => app.go(k, extra);
  const say = (t) => app.say(t);
  const openAppt = (i) => go('appt', { appt: { title: i.title, when: i.when, where: i.where || 'Personal calendar' }, apptMark: null });
  const today = D.today.map((t) => Object.assign({ isNow: false, isItem: false }, t, {
    bg: t.past ? '#f1f5f9' : '#ffffff', shadow: t.past ? 'none' : '0 0 0 1px #e2e8f0 inset',
    tc: t.past ? '#94a3b8' : (t.who ? AG[t.who].accent : '#475569'), fc: t.past ? '#94a3b8' : '#0f172a',
    open: t.who === 'pepper' ? go('checkin') : openAppt({ title: t.title === 'Leave' ? 'Dentist' : t.title, when: 'Today · ' + t.time, where: t.title === 'Dentist' || t.title === 'Leave' ? D.dentist.where : 'Personal calendar' })
  }));
  const todayRow = today.map((t) => Object.assign({ longTitle: D.longTitles[t.title] || t.title }, t));
  const A = (t, title, kind, past, where) => ({ t, title, kind: D.kinds[kind], tc: past ? '#94a3b8' : '#475569', fc: past ? '#94a3b8' : '#0f172a', deco: past ? 'line-through' : 'none', open: openAppt({ title, when: t, where }) });
  const agenda = D.agenda.map((d) => ({ day: d.day, items: d.items.map((i) => A(...i)) }));
  const appt = st.appt || D.dentist;
  const calRows = D.calendars.map((c) => { const on = st.cal[c[0]]; return { name: c[1], toggle: flip(app, 'cal', c[0]), bg: on ? '#16a34a' : '#cbd5e1', just: on ? 'flex-end' : 'flex-start' }; });
  const kindRows = D.kindNames.map((k) => ({ name: k[1], c: D.kinds[k[0]] }));
  const swatches = ['#dc2626', '#ea580c', '#eab308', '#16a34a', '#0d9488', '#2563eb', '#9333ea', '#db2777', '#64748b'].map((c) => ({ c }));
  const travelChips = D.travelWays.map((t) => Object.assign({ name: t[1], pick: () => app.setState({ travel: t[0] }) }, chip(st.travel === t[0], '#6d28d9')));
  const apptNoteRows = st.apptNotes.map((t, i) => ({ t, clear: () => { app.setState((x) => ({ apptNotes: x.apptNotes.filter((_, j) => j !== i) })); say('Note cleared'); } }));
  return {
    agent: { donna: { rows: D.rows } },
    titles: { appt: appt.title },
    values: {
      todayRow, railToday: todayRow.filter((t) => t.isItem), agenda, appt,
      apptMarked: !!st.apptMark, apptMarkText: st.apptMark === 'done' ? 'Marked as done' : 'Marked: didn’t happen as planned', apptMarkColor: st.apptMark === 'done' ? '#15803d' : '#475569',
      markDone: () => app.setState((x) => ({ apptMark: x.apptMark === 'done' ? null : 'done' })), markMissed: () => app.setState((x) => ({ apptMark: x.apptMark === 'missed' ? null : 'missed' })),
      toggleBell: () => app.setState((x) => ({ bell: !x.bell })), bellBg: st.bell ? '#16a34a' : '#cbd5e1', bellJust: st.bell ? 'flex-end' : 'flex-start',
      calRows, kindRows, swatches, saveKinds: () => { app.back(); say('Kinds saved'); },
      travelChips, travelText: D.travel[st.travel], apptNoteRows
    }
  };
}
