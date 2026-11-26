// Checks that web/app.js (the logic taken apart into areas) gives exactly the render values
// of the prototypes' own logic class, for all six prototypes, over a long walk of taps.
//   node tests/web/logic_equivalence.mjs [steps]
// No DOM needed: both components get a stub setState that merges at once.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const { Component: Ours } = await import(path.join(ROOT, 'web', 'app.js'));

class Stub {
  constructor(props) { this.props = props || {}; this.state = {}; }
  setState(u) { const p = typeof u === 'function' ? u(this.state, this.props) : u; if (p) this.state = Object.assign({}, this.state, p); }
  forceUpdate() {}
}
function original(file) {
  const src = fs.readFileSync(path.join(ROOT, 'design', file), 'utf8');
  const code = src.slice(src.indexOf('class Component extends DCLogic'), src.lastIndexOf('</script>'));
  return new Function('DCLogic', code + '\nreturn Component;')(Stub);
}
// Ours merges state at once too (DCLogic.setState), and renders nothing without a mount.
const OursStub = Ours;

// ours points at ?design=, the prototype at the other file; and what ours adds for real use:
// the text boxes' drafts, the demo flag, and handlers on the past games
// texts: its own holes (tx…, continueCall) and the bubbles' item kind (txText, txPill)
// pepper: its real screens read everything under pp; in demo mode pp is shaped from made-up sample data
const IGNORE = /^designs\.\d+\.href$|^(drafts|typed|enter)(\.|$)|^demoMode$|^pastGames\.\d+\.(open|id)$|^(bucket|wish)\.\d+\.id$|^bucket\.\d+\.open$|^cl(\.|$)|^tx[A-Z]|^continueCall$|^bubbles\.\d+\.tx|^pp(\.|$)/;
// agenda and inbox: the holes their real screens add (the filter's kinds, the kind editor's name box and swatches,
// the line under the agenda, the appointment's own description, travel's second line and link, empty and failed
// lines, his notes' Clear, the mail list); in demo mode they carry the design's own words
const IGNORE_AGENDA_INBOX = /^kindRows\.\d+\.(op|toggle|typed|swatches)(\.|$)|^filterKinds(\.|$)|^(agendaHead|agendaLooked|agendaEmpty|agendaEmptyText|agendaFailed|agendaRetry|apptTimed|apptGoogle|hasGoogle|resetKinds|hasTravel|travelSub|hasTravelSub|travelLink|hasTravelLink|travelLinkText)$|^myNotes\.\d+\.clear$|^(myNotesEmpty|herNotesEmpty|nudgesEmpty|eyesEmpty|hasCleared|notesLoading|notesFailed|notesRetry|mailItems|mailEmpty|mailLoading|mailFailed|mailRetry|mailRest)(\.|$)/;
// cl.*: the call's holes added for the real call (timer, messages, hold-to-talk, the typed line); in demo mode they carry the design's words
// todoX.* and listX.*: what the to-do and lists screens read beyond the prototype's values (counts, empty and loading
// lines, an item's real fields and folds); in demo mode they carry the design's own words
const IGNORE_TODO_LISTS = /^(todoX|listX)(\.|$)/;
// mpv.* and setv.*: what Moneypenny's screens and the settings screens read beyond the prototype's values (the status
// timeline, usage, health, sessions, hand-over text, features, voices, sound, weather); wxChip: the weather chip's
// degrees for home. In demo mode they carry the design's own words
const IGNORE_MP_SETTINGS = /^(mpv|setv)(\.|$)|^wxChip$/;
function flat(v, p, out, fns) {
  if (typeof v === 'function') { out[p] = '[fn]'; fns[p] = v; return; }
  if (v && typeof v === 'object') { for (const k of Object.keys(v)) flat(v[k], p ? p + '.' + k : k, out, fns); if (!Object.keys(v).length) out[p] = Array.isArray(v) ? '[]' : '{}'; return; }
  out[p] = v;
}
const look = (o) => { const out = {}, fns = {}; flat(o, '', out, fns); return { out, fns }; };

let seed = 7;
const rand = (n) => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed % n; };
const STEPS = Number(process.argv[2] || 1500);
let bad = 0;

for (const design of ['Desk', 'Spotlight', 'Thread']) {
  for (const device of ['iPhone', 'Mac']) {
    const file = design + '-' + device + '.dc.html';
    const Orig = original(file);
    const a = new Orig({});
    // demo mode: every area renders its demo module, wired or not, as the prototypes do
    const b = new OursStub({ design: design.toLowerCase(), device: device === 'Mac' ? 'mac' : 'phone', onDesign() {}, demo: true });
    const mismatch = [];
    const compare = (step) => {
      const x = look(a.renderVals()), y = look(b.renderVals());
      const keys = new Set(Object.keys(x.out).concat(Object.keys(y.out)));
      for (const k of keys) {
        if (IGNORE.test(k) || IGNORE_AGENDA_INBOX.test(k) || IGNORE_TODO_LISTS.test(k) || IGNORE_MP_SETTINGS.test(k)) continue;
        if (JSON.stringify(x.out[k]) !== JSON.stringify(y.out[k])) mismatch.push(step + ': ' + k + ' = ' + JSON.stringify(x.out[k]) + ' / ours ' + JSON.stringify(y.out[k]));
      }
      return { x, y };
    };
    let taps = 0;
    // First every screen once, then a long random walk over every handler.
    let { x, y } = compare('start');
    const first = Object.keys(x.fns).filter((k) => k.startsWith('nav.') || k.startsWith('open.'));
    for (let i = 0; i < first.length + STEPS && mismatch.length < 10; i++) {
      const names = Object.keys(x.fns).filter((k) => y.fns[k]);
      const name = i < first.length ? first[i] : names[rand(names.length)];
      if (!x.fns[name] || !y.fns[name]) continue;
      if (i < first.length) { a.setState({ screen: 'home', stack: [] }); b.setState({ screen: 'home', stack: [] }); ({ x, y } = compare('reset')); }
      const ev = { preventDefault() {} };
      x.fns[name](ev); y.fns[name](ev);
      taps++;
      ({ x, y } = compare(name));
    }
    const sa = JSON.stringify(Object.assign({}, a.state, { toastUndo: !!a.state.toastUndo }), Object.keys(a.state).sort());
    const sb = JSON.stringify(Object.assign({}, b.state, { toastUndo: !!b.state.toastUndo }), Object.keys(a.state).sort());
    if (sa !== sb) mismatch.push('end state differs');
    console.log((mismatch.length ? 'FAIL ' : 'ok   ') + file + ': ' + taps + ' taps compared' + (mismatch.length ? '\n  ' + mismatch.slice(0, 10).join('\n  ') : ''));
    bad += mismatch.length ? 1 : 0;
  }
}
console.log(bad ? bad + ' prototype(s) differ' : 'all six match');

// The wiring switch: an unwired area reads its demo module; a wired one reads state.data,
// null while loading; demo mode always reads the demo module.
{
  const { AREAS } = await import(path.join(ROOT, 'web', 'app.js'));
  const fake = { NAME: 'fake', WIRED: true, demo: { from: 'demo' } };
  const real = new Ours({ design: 'desk' }), shown = new Ours({ design: 'desk', demo: true });
  const checks = [
    ['every area has a NAME, a WIRED flag and a demo module', Object.values(AREAS).every((a) => typeof a.WIRED === 'boolean' && a.demo && a.NAME)],
    ['an unwired area reads its demo module', real.source(Object.assign({}, fake, { WIRED: false })).from === 'demo'],
    ['a wired area reads nothing while loading', real.source(fake) === null],
    ['a wired area reads state.data', (real.setData('fake', { from: 'server' }), real.source(fake).from === 'server')],
    ['demo mode reads the demo module', shown.source(fake).from === 'demo']
  ];
  for (const [name, ok] of checks) { console.log((ok ? 'ok   ' : 'FAIL ') + name); if (!ok) bad++; }
}
process.exit(bad ? 1 : 0);
