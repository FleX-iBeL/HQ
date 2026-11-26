// The inbox area (Donna): mail on home, his quick notes, her notes (in each of the three
// spaces), her nudges, what she keeps an eye out for, cleared notes.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
//
// Real data: state.data.inbox = { notes: the answer of GET api/notes, mail: the very important
// mail (the `mail` of GET api/todo), notesFailed / mailFailed: why a load failed }.
import * as demo from './demo/inbox.js';
import { flip } from './util.js';

export const NAME = 'inbox';
export const WIRED = true;
export const LOADING_OK = true;
export { demo };

export const start = { nudges: { passport: false, fine: false }, nbell: { passport: true, fine: true }, clearedOpen: false };

// ---- loading ----------------------------------------------------------------------------

const put = (app, part) => app.setData('inbox', (old) => Object.assign({}, old || {}, part));
async function fetchNotes(app) {
  try { put(app, { notes: await app.api.get('api/notes'), notesFailed: '' }); } catch (err) { put(app, { notesFailed: err.message || 'no answer' }); }
}
async function fetchMail(app) {
  try {
    const t = await app.api.get('api/todo');
    put(app, { mail: (t && Array.isArray(t.mail)) ? t.mail : [], mailFailed: '' });
  } catch (err) { put(app, { mailFailed: err.message || 'no answer' }); }
}
export async function load(app) { await Promise.all([fetchNotes(app), fetchMail(app)]); }
export const enter = { notes: fetchNotes, mail: fetchMail };

// A change to the notes: shown at once, then the server's answer (or back as it was, and said).
async function notesChange(app, body, patch, fail) {
  if (patch) put(app, { notes: patch(app.state.data.inbox.notes) });
  try {
    const notes = await app.api.post('api/notes', body, 'notes');
    if (notes && Array.isArray(notes.items)) put(app, { notes });
    return true;
  } catch (err) {
    app.say(fail || 'Couldn’t save that. Try again.');
    fetchNotes(app);
    return false;
  }
}

// ---- words ------------------------------------------------------------------------------

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
// "2026-11-26 10:38:27" or "2026-11-26": Today, 10:38 / Yesterday / Tuesday / 4 Nov
function when(s, withTime) {
  const m = /^(\d{4})-(\d\d)-(\d\d)(?:[ T](\d\d):(\d\d))?/.exec(String(s || ''));
  if (!m) return String(s || '');
  const d = new Date(+m[1], +m[2] - 1, +m[3]), now = new Date();
  const diff = Math.round((new Date(now.getFullYear(), now.getMonth(), now.getDate()) - d) / 864e5);
  const t = withTime && m[4] ? ', ' + m[4] + ':' + m[5] : '';
  if (diff === 0) return 'Today' + t;
  if (diff === 1) return 'Yesterday' + t;
  if (diff > 1 && diff < 7) return DAYS[d.getDay()] + t;
  return d.getDate() + ' ' + MON[d.getMonth()] + (d.getFullYear() !== now.getFullYear() ? ' ' + d.getFullYear() : '') + t;
}
const short = (t, n) => (t.length > n ? t.slice(0, n - 1).trimEnd() + '…' : t);

// ---- shaping ----------------------------------------------------------------------------

export function vals(st, ctx, D) {
  if (D === demo) return demoVals(st, ctx, D);
  const { app } = ctx;
  const notes = D && D.notes, mail = D && Array.isArray(D.mail) ? D.mail.filter((m) => !/resolved/i.test(m.status || '')) : null;
  const hers = (notes && notes.hers) || { items: [], watches: [], nudges: [] };
  const nudging = Array.isArray(hers.nudges) ? hers.nudges : [];
  const ready = !!(notes && Array.isArray(notes.items));

  const nudgeDone = (x) => () => notesChange(app, { nudge_done: x.n },
    (n) => Object.assign({}, n, { hers: Object.assign({}, n.hers, { nudges: (n.hers.nudges || []).filter((y) => y.n !== x.n) }) }), 'Couldn’t stop that nudge. Try again.')
    .then((ok) => { if (ok) app.say('Done. She stopped nudging'); });
  const nudges = nudging.map((x) => ({ title: x.text, sub: x.paused ? 'Paused for now' : 'She’s nudging you until it’s done', label: 'Done', deco: 'none', fc: '#0f172a', toggle: nudgeDone(x) }));
  const nudgeRows = nudging.map((x) => ({ t: x.text, when: x.paused ? 'Paused for now' : 'Nudging you until it’s done',
    bell: () => {}, bellBg: x.paused ? '#f1f5f9' : '#f5f3ff', bellFg: x.paused ? '#94a3b8' : '#6d28d9', bellAria: x.paused ? 'Paused for now' : 'Nudging you',
    done: nudgeDone(x), doneLabel: 'Done' }));

  // Newest first, as the design lists them.
  const myNotes = ready ? notes.items.slice().reverse().map((it) => ({ id: it.id, t: it.text, when: when(it.when, true),
    clear: () => notesChange(app, { clear: it.id }, (n) => Object.assign({}, n, { items: n.items.filter((y) => y.id !== it.id) }), 'Couldn’t clear that note. Try again.')
      .then((ok) => { if (ok) app.say('Cleared the note'); }) })) : [];
  const addNote = (text) => notesChange(app, { add: text }, (n) => Object.assign({}, n, { items: n.items.concat([{ id: 'new-' + Date.now(), when: '', text }]) }), 'Couldn’t save that note. Try again.');
  // Only Donna keeps notes of her own in HQ; Pepper's and Moneypenny's lists are empty until HQ keeps theirs.
  const herNotes = st.space === 'donna' && Array.isArray(hers.items) ? hers.items.map((it) => ({ t: it.text, when: when(it.when, false) })) : [];
  const eyeRows = (hers.watches || []).map((w) => ({ t: w.text,
    when: [w.until ? 'until ' + when(w.until, false) : '', w.matches ? w.matches + (w.matches === 1 ? ' update' : ' updates') : ''].filter(Boolean).join(' · ') || 'always' }));
  // Cleared notes come only if the server sends them (`cleared` on api/notes); it doesn't yet.
  const clearedRows = ready && Array.isArray(notes.cleared) ? notes.cleared.map((c) => ({ t: c.text, when: 'Cleared ' + when(c.cleared, false).toLowerCase() })) : [];

  const mailItems = (mail || []).map((m) => ({ subject: m.subject || '(no subject)', from: 'From ' + (m.from || 'someone') + ' · ' + when(m.when, false).toLowerCase(),
    what: m.what || '', onList: /on the list/i.test(m.status || '') }));
  const nMail = mailItems.length;
  const mine = myNotes.length, herCount = (hers.items || []).length;
  const homeLines = { nudges: { t: nudging.length ? nudging.length + (nudging.length === 1 ? ' nudge: ' : ' nudges: ') + nudging.map((x) => short(x.text, 28)).join(', ') : 'No nudges left', c: '#0f172a', w: '400' } };
  if (nMail) homeLines.mail = { t: nMail + ' very important mail', c: '#b42318', w: '600' };
  const retry = (what) => () => { put(app, { [what + 'Failed']: '' }); (what === 'notes' ? fetchNotes : fetchMail)(app); };

  return {
    agent: { donna: { rows: {
      mail: ['Mail', mail ? (nMail ? nMail + ' very important' : 'Nothing important') : (D && D.mailFailed ? 'Didn’t load' : ''), 'mail', nMail ? '#b42318' : '#475569', nMail ? '600' : '400'],
      notes: ['Notes', ready ? (mine ? mine + ' of yours' : 'None of yours') + (herCount ? ', ' + herCount + ' of hers' : '') : '', 'notes']
    }, homeLines } },
    submit: { inboxNote: addNote },
    values: {
      nudges, nudgeCount: nudging.length, nudgeRows,
      myNotes, myNotesEmpty: ready && !mine, herNotes, herNotesEmpty: ready && !herNotes.length, isDonnaNotes: st.space === 'donna',
      nudgesEmpty: !nudging.length, eyesEmpty: !eyeRows.length,
      eyeRows, clearedRows, hasCleared: clearedRows.length > 0, clearedOpen: st.clearedOpen,
      toggleCleared: () => app.setState((x) => ({ clearedOpen: !x.clearedOpen })), clearedLabel: st.clearedOpen ? 'Hide cleared notes' : 'Show cleared notes (' + clearedRows.length + ')',
      notesLoading: !ready && !(D && D.notesFailed), notesFailed: !!(D && D.notesFailed), notesRetry: retry('notes'),
      mailItems, mailEmpty: !!mail && !nMail, mailLoading: !mail && !(D && D.mailFailed), mailFailed: !!(D && D.mailFailed), mailRetry: retry('mail'), mailRest: false
    }
  };
}

// The made-up content, shaped exactly as the prototypes do (demo mode). The mail screen's one
// example is the prototypes' own text, which their markup had written in.
const DEMO_MAIL = [{ subject: 'Your contract is ready to sign', from: 'From the landlord · this morning', what: 'Donna flagged it because it has a deadline: Monday.', onList: false }];
function demoVals(st, ctx, D) {
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
  // The real screens also give each of his notes a Clear; here it does nothing.
  const myNotes = D.myNotes.map((n) => Object.assign({ clear: () => {} }, n));
  return {
    agent: { donna: { rows: D.rows, homeLines: Object.assign({ nudges: { t: allDone ? D.nudgeLines.none : D.nudgeLines.left, c: '#0f172a', w: '400' } }, D.homeLines) } },
    submit: { inboxNote: () => {} },
    values: {
      nudges, nudgeCount, nudgeRows,
      myNotes, myNotesEmpty: false, herNotes: D.notesBy[st.space], herNotesEmpty: false, isDonnaNotes: st.space === 'donna', nudgesEmpty: false, eyesEmpty: false,
      eyeRows: D.eyeRows, clearedRows: D.clearedRows, hasCleared: true, clearedOpen: st.clearedOpen,
      toggleCleared: () => app.setState((x) => ({ clearedOpen: !x.clearedOpen })), clearedLabel: st.clearedOpen ? 'Hide cleared notes' : 'Show cleared notes (' + D.clearedRows.length + ')',
      notesLoading: false, notesFailed: false, notesRetry: () => {},
      mailItems: DEMO_MAIL, mailEmpty: false, mailLoading: false, mailFailed: false, mailRetry: () => {}, mailRest: true
    }
  };
}
