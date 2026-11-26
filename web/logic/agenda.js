// The agenda area (Donna): today across the three, the agenda, an appointment, travel,
// the kinds of time, the calendar filter. Also Donna's card (her next appointment).
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
//
// Real data: state.data.agenda = { cal: the answer of GET api/calendar, coaching: the check-ins
// of GET api/coaching (for Pepper's items on today's row), failed: why the last load failed }.
// Which calendars and kinds are hidden is kept on this device (localStorage hq-cal-off and
// hq-kind-off), as the old page does. Google Calendar itself is never changed.
import * as demo from './demo/agenda.js';
import { chip, flip } from './util.js';

export const NAME = 'agenda';
export const WIRED = true;
export const LOADING_OK = true;
export { demo };

export const start = { apptMark: null, bell: true, appt: null, travel: 'bike', apptNotes: demo.apptNotes.slice(), cal: { personal: true, work: true, birthdays: true },
  apptId: null, calOff: null, kindOff: null, kindDraft: {}, agEarlier: false };

// ---- loading ----------------------------------------------------------------------------

const CAL_OFF = 'hq-cal-off', KIND_OFF = 'hq-kind-off';
function readSet(key) { try { const v = JSON.parse(localStorage.getItem(key) || '[]'); return Array.isArray(v) ? v : []; } catch (e) { return []; } }
function writeSet(key, list) { try { localStorage.setItem(key, JSON.stringify(list)); } catch (e) { /* private window: this view only */ } }

let polls = 0, pollTimer = null;
async function fetchCal(app, fresh) {
  try {
    const cal = await app.api.get('api/calendar' + (fresh ? '?fresh=1' : ''));
    app.setData('agenda', (old) => Object.assign({}, old || {}, { cal, failed: '' }));
    clearTimeout(pollTimer);
    // A fresh read from Google takes a moment: ask again while it's reading, a few times at most.
    if (cal && cal.looking && polls < 10) { polls++; pollTimer = setTimeout(() => fetchCal(app, false), 4000); } else polls = 0;
  } catch (err) {
    app.setData('agenda', (old) => Object.assign({}, old || {}, { failed: err.message || 'no answer' }));
  }
}
async function fetchCoaching(app) {
  try {
    const c = await app.api.get('api/coaching');
    app.setData('agenda', (old) => Object.assign({}, old || {}, { coaching: (c && Array.isArray(c.checkins)) ? c.checkins : [] }));
  } catch (err) { /* Pepper's items just don't show on today's row */ }
}
export async function load(app) {
  if (app.state.calOff == null) app.setState({ calOff: readSet(CAL_OFF), kindOff: readSet(KIND_OFF) });
  await Promise.all([fetchCal(app, false), fetchCoaching(app)]);
}
// Opening the agenda asks Google again when HQ's copy is older than a quarter of an hour (the server decides).
export const enter = { agenda: (app) => { polls = 0; return fetchCal(app, true); } };

// A change: show it at once, send it, then take the server's answer (or put it back and say so).
async function change(app, path, body, patch, fail) {
  if (patch) app.setData('agenda', (old) => Object.assign({}, old, { cal: patch(old.cal) }));
  try {
    const cal = await app.api.post(path, body, 'calendar');
    if (cal && Array.isArray(cal.events)) app.setData('agenda', (old) => Object.assign({}, old, { cal }));
    return cal || {};
  } catch (err) {
    app.say(fail || 'Couldn’t change that. Try again.');
    fetchCal(app, false);
    return null;
  }
}
const patchEvent = (id, fn) => (cal) => Object.assign({}, cal, { events: cal.events.map((e) => (e.id === id ? fn(e) : e)) });

// ---- dates ------------------------------------------------------------------------------

const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const toDate = (iso) => { if (!iso) return null; const d = new Date(iso.length === 10 ? iso + 'T00:00:00' : iso); return isNaN(d) ? null : d; };
const hm = (d) => String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
const midnight = (d) => new Date(d.getFullYear(), d.getMonth(), d.getDate());
const dayKey = (d) => d.getFullYear() + '-' + d.getMonth() + '-' + d.getDate();
function dayName(d, now) {
  const diff = Math.round((midnight(d) - midnight(now)) / 864e5);
  if (diff === 0) return 'Today';
  if (diff === 1) return 'Tomorrow';
  if (diff === -1) return 'Yesterday';
  return DAYS[d.getDay()] + ' ' + d.getDate() + (d.getMonth() !== now.getMonth() ? ' ' + MONTHS[d.getMonth()] : '');
}
// The day an appointment is listed under: its own, or today while one from before is still on.
function shownDay(e, now) {
  const a = toDate(e.start), z = toDate(e.end) || a, today = midnight(now);
  if (!a) return null;
  if (a >= today) return midnight(a);
  if (e.all_day ? z > today : z > now) return today;
  return midnight(a);
}
function isPast(e, now) {
  const a = toDate(e.start), z = toDate(e.end);
  if (!a) return false;
  if (e.all_day) return (z || new Date(midnight(a).getTime() + 864e5)) <= midnight(now);
  return (z || a) <= now;
}
function whenText(e, now) {
  const a = toDate(e.start), z = toDate(e.end);
  if (!a) return e.start || '';
  const day = dayName(a, now);
  if (e.all_day) return day + ' · all day';
  return day + ' · ' + hm(a) + (z ? ' to ' + hm(z) : '');
}
function inText(mins) {
  if (mins < 1) return 'now';
  if (mins < 60) return 'in ' + mins + (mins === 1 ? ' minute' : ' minutes');
  const h = Math.round(mins / 60);
  return 'in ' + h + (h === 1 ? ' hour' : ' hours');
}
function lookedText(cal, now) {
  if (!cal) return '';
  if (cal.looking) return 'Reading your calendar…';
  if (cal.error) return 'Couldn’t read your calendar just now' + (cal.looked ? '; this is the last read' : '');
  if (!cal.looked) return '';
  const m = Math.round((now.getTime() / 1000 - cal.looked) / 60);
  return 'Read from your calendar ' + (m < 1 ? 'just now' : m < 60 ? m + (m === 1 ? ' minute' : ' minutes') + ' ago' : Math.round(m / 60) + ' h ago');
}
const short = (t, n) => (t.length > n ? t.slice(0, n - 1).trimEnd() + '…' : t);
// A note's time ("2026-11-26 10:38" or ISO): Today, 10:38 / Yesterday, 10:38 / Tuesday 24, 10:38.
function noteWhen(s, now) {
  const m = /^(\d{4})-(\d\d)-(\d\d)(?:[ T](\d\d):(\d\d))?/.exec(String(s || ''));
  if (!m) return '';
  const d = new Date(+m[1], +m[2] - 1, +m[3]);
  return dayName(d, now) + (m[4] ? ', ' + m[4] + ':' + m[5] : '');
}

// Google's eleven event colours, which a kind of time can take.
const GOOGLE = [['lavender', '#7986cb'], ['sage', '#33b679'], ['grape', '#8e24aa'], ['flamingo', '#e67c73'], ['banana', '#f6bf26'], ['tangerine', '#f4511e'],
  ['peacock', '#039be5'], ['graphite', '#616161'], ['blueberry', '#3f51b5'], ['basil', '#0b8043'], ['tomato', '#d50000']];
const HEX = Object.fromEntries(GOOGLE);
const TRAVEL_WAYS = [['bike', 'Bike'], ['transit', 'Public transport'], ['car', 'Car']];

// A calendar's own colour can be near white; its dot then takes the design's grey.
function dotColour(c) {
  const m = /^#([0-9a-f]{6})$/i.exec(c || '');
  if (!m) return '#cbd5e1';
  const n = parseInt(m[1], 16), lum = (0.299 * (n >> 16) + 0.587 * ((n >> 8) & 255) + 0.114 * (n & 255)) / 255;
  return lum > 0.9 ? '#cbd5e1' : c;
}
const viewOf = (e) => e.view || e.calendar || 'Main';
function visible(cal, st) {
  const off = new Set(st.calOff || []), koff = new Set(st.kindOff || []);
  return (cal.events || []).filter((e) => !off.has(viewOf(e)) && !(e.kind && koff.has(e.kind)));
}

// ---- Donna's card -----------------------------------------------------------------------

function nextUp(events, now) {
  return events.filter((e) => !e.all_day && !e.free && toDate(e.start) && (toDate(e.end) || toDate(e.start)) > now)
    .sort((a, b) => toDate(a.start) - toDate(b.start))[0] || null;
}
export const card = (st, D) => {
  if (D === demo) return D.card;
  const cal = D && D.cal;
  if (!cal || !Array.isArray(cal.events)) return { kicker: 'Next', headline: D && D.failed ? 'Your calendar didn’t load' : 'Reading your calendar…', sub: '', line: '' };
  if (cal.on === false) return { kicker: 'Next', headline: 'The calendar is off', sub: 'Turn it on in Settings', line: '' };
  const now = new Date(), e = nextUp(visible(cal, st), now);
  if (!e) return { kicker: 'Next', headline: 'Nothing coming up', sub: 'Nothing in the next two weeks', line: '' };
  const a = toDate(e.start), z = toDate(e.end), mins = Math.round((a - now) / 6e4);
  const day = midnight(a).getTime() === midnight(now).getTime() ? '' : dayName(a, now).toLowerCase() + ' ';
  const kicker = a <= now ? 'Now · until ' + hm(z || a) : 'Next · ' + (day ? day + 'at ' + hm(a) : inText(mins));
  const tv = e.travel || {};
  const sub = tv.on && tv.drive ? tv.drive : tv.on && tv.train ? tv.train : ((e.where && !/^https?:\/\//i.test(e.where) ? e.where : '') || (/^https?:\/\//i.test(e.where || '') ? 'Online' : '') || (viewOf(e) !== 'Main' ? viewOf(e) + ' calendar' : ''));
  return { kicker, headline: e.title + ' at ' + hm(a), sub, line: '' };
};

// ---- shaping ----------------------------------------------------------------------------

export function vals(st, ctx, D) {
  if (D === demo) return demoVals(st, ctx, D);
  const { app, AG } = ctx;
  const now = new Date();
  const cal = D && D.cal;
  const ready = !!(cal && Array.isArray(cal.events));
  const events = ready ? visible(cal, st).slice().sort((a, b) => (toDate(a.start) || 0) - (toDate(b.start) || 0)) : [];
  const kinds = ready && Array.isArray(cal.kinds) ? cal.kinds : [];
  const kindOf = (id) => kinds.find((k) => k.id === id) || null;
  const openAppt = (e) => () => app.go('appt', { apptId: e.id });
  const retry = () => { app.setData('agenda', (old) => Object.assign({}, old, { failed: '' })); load(app); };

  // Today, across the three: Donna's appointments and Pepper's check-ins that are due.
  const tmid = midnight(now), tk = dayKey(now);
  const todayEvents = events.filter((e) => { const d = shownDay(e, now); return d && dayKey(d) === tk; });
  const items = todayEvents.map((e) => {
    const a = toDate(e.start);
    return { at: e.all_day ? tmid.getTime() - 1 : a.getTime(), started: e.all_day || a <= now, time: e.all_day ? 'Day' : hm(a), title: e.title, past: isPast(e, now), who: 'donna', open: openAppt(e) };
  });
  for (const c of (D && D.coaching) || []) {
    if (!c.due) continue;
    const f = toDate(c.from), onToday = f && dayKey(f) === tk;
    items.push({ at: onToday ? f.getTime() : tmid.getTime() - 1, started: !onToday || f <= now, time: onToday ? hm(f) : 'Due', title: c.title || 'Check-in', past: false, who: 'pepper', open: () => app.go('checkin') });
  }
  items.sort((x, y) => x.at - y.at);
  const todayRow = [];
  let nowPlaced = false;
  for (const t of items) {
    if (!nowPlaced && !t.started) { todayRow.push({ isNow: true, isItem: false }); nowPlaced = true; }
    todayRow.push({
      isNow: false, isItem: true, time: t.time, title: short(t.title, 26), longTitle: t.title, past: t.past, who: t.who,
      bg: t.past ? '#f1f5f9' : '#ffffff', shadow: t.past ? 'none' : '0 0 0 1px #e2e8f0 inset',
      tc: t.past ? '#94a3b8' : AG[t.who].accent, fc: t.past ? '#94a3b8' : '#0f172a', open: t.open
    });
  }
  if (ready && !nowPlaced) todayRow.push({ isNow: true, isItem: false });

  // The agenda: from today, two weeks ahead, by day; the days of this week before today fold away above it.
  // Each row: its second line (the calendar, the place, his notes on it), the bell when she texts at its start,
  // and once it has started, Done and Didn't happen right on the row (a second tap takes the mark off).
  const markOn = (e, want) => (ev) => {
    if (ev && ev.stopPropagation) ev.stopPropagation();
    if (!e.mark_id) return;
    const was = e.mark || '', to = was === want ? '' : want;
    const put = (m) => change(app, 'api/calendar/mark', { id: e.mark_id, mark: m }, patchEvent(e.id, (x) => Object.assign({}, x, { mark: m })), 'Couldn’t mark that. Try again.');
    put(to).then((r) => { if (r) app.say(to === 'done' ? 'Marked as done' : to === 'x' ? 'Marked: didn’t happen as planned' : 'Mark taken off', () => put(was)); });
  };
  const rowOf = (e) => {
    const past = isPast(e, now), a = toDate(e.start), x = e.mark === 'x', done = e.mark === 'done';
    const url = /^https?:\/\//i.test(e.where || '');
    const notesList = (e.appt_notes || []).map((n) => n.text).filter(Boolean);
    const grey = past || x, started = !!e.mark || (!!a && a <= now);
    return { id: e.id, t: e.all_day ? 'Day' : hm(a), title: e.title, kind: dotColour(e.color),
      tc: grey ? '#94a3b8' : '#475569', fc: grey ? '#94a3b8' : e.free ? '#475569' : '#0f172a', deco: grey ? 'line-through' : 'none', open: openAppt(e),
      sub: [viewOf(e) !== 'Main' ? viewOf(e) : '', url ? 'Online' : (e.where || ''), e.free ? 'Shown as free' : ''].filter(Boolean).join(' · '),
      notesLine: notesList.join(' · '), ping: !!e.ping,
      marks: started, chev: started ? 'none' : 'block', padR: started ? '10px' : '18px', noMark: !e.mark_id, markOp: e.mark_id ? 1 : 0.4,
      done: markOn(e, 'done'), doneOn: done ? 'true' : 'false', doneBg: done ? '#16a34a' : '#ffffff', doneFg: done ? '#ffffff' : '#94a3b8', doneRing: done ? '#16a34a' : '#cbd5e1',
      miss: markOn(e, 'x'), missOn: x ? 'true' : 'false', missBg: x ? '#475569' : '#ffffff', missFg: x ? '#ffffff' : '#94a3b8', missRing: x ? '#475569' : '#cbd5e1',
      doneAria: done ? 'Done. Tap to take the mark off' : 'Done', missAria: x ? 'Didn’t happen as planned. Tap to take the mark off' : 'Didn’t happen as planned' };
  };
  const byDay = [], before = [];
  for (const e of events) {
    const d = shownDay(e, now);
    if (!d) continue;
    const into = d < tmid ? before : byDay;
    const k = dayKey(d);
    let g = into[into.length - 1];
    if (!g || g.k !== k) { g = { k, day: dayName(d, now), items: [] }; into.push(g); }
    g.items.push(rowOf(e));
  }
  const agenda = byDay.map((g) => ({ day: g.day, items: g.items }));
  const earlier = before.map((g) => ({ day: g.day, items: g.items }));
  const nBefore = before.reduce((n, g) => n + g.items.length, 0);
  const agX = { hasEarlier: nBefore > 0, earlierOpen: !!st.agEarlier && nBefore > 0, earlier, earlierAria: st.agEarlier ? 'true' : 'false',
    earlierLabel: (st.agEarlier ? 'Hide earlier this week' : 'Earlier this week') + ' · ' + nBefore,
    toggleEarlier: () => app.setState((x) => ({ agEarlier: !x.agEarlier })) };
  const hidden = ready ? (cal.events.length - events.length) : 0;
  const agendaEmpty = ready && !agenda.length;
  const agendaEmptyText = !ready ? '' : cal.on === false ? 'The calendar is off. Turn it on in Settings.' : hidden ? 'Everything is switched off in this view' : cal.looking ? 'Reading your calendar…' : cal.looked ? 'Nothing in the next two weeks' : 'Not read yet';

  // The filter: calendars and kinds, hidden on this device only.
  const cals = ready ? (cal.calendars && cal.calendars.length ? cal.calendars : [...new Set(cal.events.map(viewOf))].map((name) => ({ name }))) : [];
  const off = new Set(st.calOff || []), koff = new Set(st.kindOff || []);
  const flipIn = (key, store, id) => () => {
    const cur = new Set(app.state[key] || []);
    if (cur.has(id)) cur.delete(id); else cur.add(id);
    const list = [...cur]; writeSet(store, list); app.setState({ [key]: list });
  };
  const calRows = cals.map((c) => { const on = !off.has(c.name); return { name: c.name === 'Main' ? 'Main calendar' : c.name, toggle: flipIn('calOff', CAL_OFF, c.name), bg: on ? '#16a34a' : '#cbd5e1', just: on ? 'flex-end' : 'flex-start' }; });
  const used = new Set(ready ? cal.events.map((e) => e.kind).filter(Boolean) : []);
  const draftOf = (k) => Object.assign({ name: k.name, colour: k.colour }, st.kindDraft[k.id] || {});
  const setDraft = (id, part) => app.setState((x) => ({ kindDraft: Object.assign({}, x.kindDraft, { [id]: Object.assign({}, x.kindDraft[id] || {}, part) }) }));
  const kindRows = kinds.map((k) => {
    const dr = draftOf(k), on = !koff.has(k.id);
    return { id: k.id, name: dr.name, c: HEX[dr.colour] || k.color, op: on ? 1 : 0.4, toggle: flipIn('kindOff', KIND_OFF, k.id),
      typed: (ev) => setDraft(k.id, { name: ev.target.value }),
      swatches: GOOGLE.map(([n, hex]) => ({ c: hex, name: n, ring: n === dr.colour ? '0 0 0 2px #ffffff, 0 0 0 4px #0f172a' : 'none', pick: () => setDraft(k.id, { colour: n }) })) };
  });
  const filterKinds = kindRows.filter((k) => !kindOf(k.id).template || used.has(k.id));
  const calsOn = cals.filter((c) => !off.has(c.name)).length, kindsOn = filterKinds.filter((k) => !koff.has(k.id)).length;
  const agendaHead = (calsOn === cals.length ? 'All calendars' : calsOn + ' of ' + cals.length + ' calendars') + ' · '
    + (kindsOn === filterKinds.length ? 'all kinds of time' : kindsOn + ' of ' + filterKinds.length + ' kinds of time');
  const saveKinds = async () => {
    const bodies = [];
    for (const k of kinds) {
      const dr = draftOf(k), body = { id: k.id };
      if (dr.name.trim() && dr.name.trim() !== k.name) body.name = dr.name.trim();
      if (dr.colour !== k.colour) body.colour = dr.colour;
      if (body.name || body.colour) bodies.push(body);
    }
    for (const body of bodies) { if (!(await change(app, 'api/calendar/kind', body, null, 'Couldn’t save the kinds. Try again.'))) return; }
    app.setState({ kindDraft: {} }); app.back(); app.say('Kinds saved');
  };
  const resetKinds = async () => {
    for (const k of kinds.filter((x) => x.own)) { if (!(await change(app, 'api/calendar/kind', { id: k.id, reset: true }, null, 'Couldn’t change the kinds back. Try again.'))) return; }
    app.setState({ kindDraft: {} }); app.say('HQ’s own names and colours are back');
  };

  // One appointment.
  const e = ready ? (cal.events.find((x) => x.id === st.apptId) || null) : null;
  const key = e ? (e.mark_id || e.id) : '';
  const kd = e && e.kind ? kindOf(e.kind) : null;
  const appt = e ? { title: e.title, when: whenText(e, now), where: [e.where, viewOf(e) !== 'Main' ? viewOf(e) + ' calendar' : '', kd ? kd.name : '', e.free ? 'Shown as free' : ''].filter(Boolean).join(' · ') }
    : { title: st.apptId && ready ? 'Not in your calendar any more' : '', when: '', where: '' };
  const mark = (want) => () => {
    if (!e || !e.mark_id) return;
    const was = e.mark || '', to = was === want ? '' : want, id = e.id, mid = e.mark_id;
    const put = (m) => change(app, 'api/calendar/mark', { id: mid, mark: m }, patchEvent(id, (x) => Object.assign({}, x, { mark: m })), 'Couldn’t mark that. Try again.');
    put(to).then((r) => { if (r) app.say(to === 'done' ? 'Marked as done' : to === 'x' ? 'Marked: didn’t happen as planned' : 'Mark taken off', () => put(was)); });
  };
  const toggleBell = () => {
    if (!e) return;
    const on = !e.ping;
    change(app, 'api/calendar/ping', { id: e.id, on }, patchEvent(e.id, (x) => Object.assign({}, x, { ping: on })));
  };
  const tv = (e && e.travel) || null;
  const modes = (tv && tv.modes) || [];
  const travelChips = TRAVEL_WAYS.map(([id, name]) => Object.assign({ name, pick: () => {
    if (!e || !tv) return;
    if (id === 'bike') { app.say('HQ can’t plan bike trips yet'); return; }
    if (!modes.includes(id)) { app.say('Driving is off. Turn it on in Settings.'); return; }
    const body = tv.on && tv.mode === id ? { id: e.id, on: false, mode: id } : { id: e.id, on: true, mode: id };
    change(app, 'api/calendar/travel', body, patchEvent(e.id, (x) => Object.assign({}, x, { travel: Object.assign({}, x.travel, { on: body.on, mode: id }) })));
  } }, chip(!!(tv && tv.on && tv.mode === id), '#6d28d9')));
  let travelText = '', travelSub = '';
  if (tv) {
    const car = tv.mode === 'car';
    if (!tv.on) travelText = 'Travel is off. Pick a way and Donna keeps you up to date.';
    else if (tv.why_not) travelText = car && /key/i.test(tv.why_not) ? 'No maps key yet: add yours in Settings, under Driving.' : car ? 'Not found yet: ' + tv.why_not : 'Not found yet: tell Donna where it is, or where you leave from.';
    else if (!tv.link) travelText = 'The trip is looked up within the hour.';
    else travelText = car && tv.drive ? tv.drive : 'From ' + (tv.from === 'home' ? 'home' : tv.from) + (tv.after ? ' (after ' + tv.after + ')' : '') + ' to ' + tv.to;
    if (tv.on && tv.link) travelSub = [!car && tv.train ? 'Train: ' + tv.train : (!car && tv.stations && tv.stations.length === 2 ? 'Stations: ' + tv.stations.join(' to ') : '')].concat(tv.news || []).filter(Boolean).join(' · ');
  }
  const apptNoteRows = ((e && e.appt_notes) || []).map((n) => ({ id: n.id, t: n.text, when: noteWhen(n.when, now), clear: () => {
    change(app, 'api/calendar/note', { id: key, clear: n.id }, patchEvent(e.id, (x) => Object.assign({}, x, { appt_notes: (x.appt_notes || []).filter((y) => y.id !== n.id) })), 'Couldn’t clear the note. Try again.')
      .then((r) => { if (r) app.say('Note cleared', () => change(app, 'api/calendar/note', { id: key, add: n.text }, null, 'Couldn’t bring the note back. Try again.')); });
  } }));
  const addApptNote = (text) => {
    if (!e) return;
    change(app, 'api/calendar/note', { id: key, add: text }, patchEvent(e.id, (x) => Object.assign({}, x, { appt_notes: (x.appt_notes || []).concat([{ id: 'new-' + Date.now(), text, when: '' }]) })), 'Couldn’t save the note. Try again.');
  };

  // The to-do items planned in this block (by hand, on the item's page or on a call).
  const tdLists = (st.data && st.data.todo && Array.isArray(st.data.todo.lists)) ? st.data.todo.lists : [];
  const plannedHere = [];
  if (e) for (const l of tdLists) {
    if (['done', 'letgo', 'groceries', 'grocoff'].includes(l.kind)) continue;
    for (const it of l.items || []) {
      const pl = it.planned;
      if (pl && (pl.id === e.id || (e.mark_id && pl.id === e.mark_id))) plannedHere.push({ id: it.id, t: it.title, list: l.name, open: () => app.go('todoItem', { tdItem: it.id, tdList: l.key }) });
    }
  }
  agX.planned = plannedHere; agX.hasPlanned = plannedHere.length > 0;

  const todayCount = todayEvents.length;
  return {
    agent: { donna: { rows: { agenda: ['Agenda', ready ? (todayCount ? todayCount + ' today' : 'Nothing today') : (D && D.failed ? 'Didn’t load' : ''), 'agenda'] } } },
    titles: { appt: appt.title },
    submit: { agendaApptNote: addApptNote },
    values: {
      todayRow, railToday: todayRow.filter((t) => t.isItem), agenda, appt,
      agendaHead, agendaLooked: D && D.failed ? '' : (ready ? lookedText(cal, now) : 'Reading your calendar…'),
      agendaEmpty, agendaEmptyText, agendaFailed: !!(D && D.failed), agendaRetry: retry,
      apptMarked: !!(e && e.mark), apptMarkText: e && e.mark === 'done' ? 'Marked as done' : 'Marked: didn’t happen as planned', apptMarkColor: e && e.mark === 'done' ? '#15803d' : '#475569',
      markDone: mark('done'), markMissed: mark('x'),
      apptTimed: !!(e && !e.all_day), toggleBell, bellBg: e && e.ping ? '#16a34a' : '#cbd5e1', bellJust: e && e.ping ? 'flex-end' : 'flex-start',
      apptGoogle: (e && e.notes) || '', hasGoogle: !!(e && e.notes),
      calRows, kindRows, filterKinds, swatches: GOOGLE.map(([, c]) => ({ c })), saveKinds, resetKinds,
      hasTravel: !!tv, travelChips, travelText, travelSub, hasTravelSub: !!travelSub, travelLink: (tv && tv.on && tv.link) || '', hasTravelLink: !!(tv && tv.on && tv.link),
      travelLinkText: tv && tv.mode === 'car' ? 'Open in Google Maps' : 'Open the route', apptNoteRows, agX
    }
  };
}

// The made-up content, shaped exactly as the prototypes do (demo mode).
function demoVals(st, ctx, D) {
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
  const swatches = ['#dc2626', '#ea580c', '#eab308', '#16a34a', '#0d9488', '#2563eb', '#9333ea', '#db2777', '#64748b'].map((c) => ({ c }));
  // The kind rows also carry what the real screens use (the filter toggle, the name box, a swatch pick); here they do nothing.
  const kindRows = D.kindNames.map((k) => ({ name: k[1], c: D.kinds[k[0]], op: 1, toggle: () => {}, typed: () => {}, swatches: swatches.map((w) => ({ c: w.c, ring: 'none', pick: () => {} })) }));
  const travelChips = D.travelWays.map((t) => Object.assign({ name: t[1], pick: () => app.setState({ travel: t[0] }) }, chip(st.travel === t[0], '#6d28d9')));
  const apptNoteRows = st.apptNotes.map((t, i) => ({ t, clear: () => { app.setState((x) => ({ apptNotes: x.apptNotes.filter((_, j) => j !== i) })); say('Note cleared'); } }));
  return {
    agent: { donna: { rows: D.rows } },
    titles: { appt: appt.title },
    submit: { agendaApptNote: (text) => app.setState((x) => ({ apptNotes: x.apptNotes.concat([text]) })) },
    values: {
      todayRow, railToday: todayRow.filter((t) => t.isItem), agenda, appt,
      agendaHead: 'All calendars · all kinds of time', agendaLooked: 'Read from your calendar 2 minutes ago', agendaEmpty: false, agendaEmptyText: '', agendaFailed: false, agendaRetry: () => {},
      apptMarked: !!st.apptMark, apptMarkText: st.apptMark === 'done' ? 'Marked as done' : 'Marked: didn’t happen as planned', apptMarkColor: st.apptMark === 'done' ? '#15803d' : '#475569',
      markDone: () => app.setState((x) => ({ apptMark: x.apptMark === 'done' ? null : 'done' })), markMissed: () => app.setState((x) => ({ apptMark: x.apptMark === 'missed' ? null : 'missed' })),
      apptTimed: true, toggleBell: () => app.setState((x) => ({ bell: !x.bell })), bellBg: st.bell ? '#16a34a' : '#cbd5e1', bellJust: st.bell ? 'flex-end' : 'flex-start',
      apptGoogle: 'Six-monthly check-up. Bring your insurance card.', hasGoogle: true,
      calRows, kindRows, filterKinds: kindRows, swatches, saveKinds: () => { app.back(); say('Kinds saved'); }, resetKinds: () => {},
      hasTravel: true, travelChips, travelText: D.travel[st.travel], travelSub: 'Light rain from 16:00, dry on the way there', hasTravelSub: true, travelLink: '#', hasTravelLink: true, travelLinkText: 'Open the route', apptNoteRows
    }
  };
}
