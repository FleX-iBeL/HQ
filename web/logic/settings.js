// The settings area: settings and the design picker, features, voices, sound, weather,
// the tutorial and its tour, and the states to try: first run, Free, offline, texts off,
// an incoming call.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/settings.js';

export const NAME = 'settings';
export const WIRED = false;
export { demo };
import { DESIGNS } from './core.js';

export const start = {
  rain: true, offline: false, fresh: false, free: false,
  feat: Object.assign({}, demo.featuresOn), voices: Object.assign({}, demo.voicesPicked), place: 'here', tour: -1
};

const sw = (on) => ({ bg: on ? '#16a34a' : '#cbd5e1', just: on ? 'flex-end' : 'flex-start' });

export function vals(st, ctx, D) {
  const { app, AG, sc } = ctx;
  const say = (t) => app.say(t);

  // The design picker: switches the app's design in place, keeping where you are.
  const designs = DESIGNS.map((d) => {
    const on = st.design === d.id;
    return { name: d.name, line: d.line, on: on ? 'true' : 'false', ring: on ? '7px solid #0f172a' : '2px solid #cbd5e1',
      href: '?design=' + d.id, pick: (e) => { if (e && e.preventDefault) e.preventDefault(); app.useDesign(d.id); } };
  });

  const FEAT = D.features;
  const featRows = FEAT.map((f) => {
    const on = st.feat[f[0]]; const blocked = !!f[3] && !st.feat[f[3]]; const need = f[3] ? FEAT.filter((x) => x[0] === f[3])[0][1] : '';
    return { name: f[1], line: blocked ? 'Needs ' + need + ': turn that on first' : f[2],
      toggle: () => { if (!blocked) app.setState((x) => ({ feat: Object.assign({}, x.feat, { [f[0]]: !x.feat[f[0]] }) })); },
      bg: blocked ? '#e2e8f0' : (on ? '#16a34a' : '#cbd5e1'), just: on && !blocked ? 'flex-end' : 'flex-start', op: blocked ? 0.5 : 1 };
  });
  const featCount = FEAT.filter((f) => st.feat[f[0]] && !(f[3] && !st.feat[f[3]])).length;

  const voiceGroups = ['donna', 'pepper', 'mp'].map((k) => ({ name: AG[k].name, color: AG[k].color, ink: AG[k].ink, initial: AG[k].initial,
    opts: D.voices[k].map((v) => { const on = st.voices[k] === v; return { v, pick: () => app.setState((x) => ({ voices: Object.assign({}, x.voices, { [k]: v }) })), ring: on ? '7px solid ' + AG[k].color : '2px solid #cbd5e1' }; }) }));
  const placeChips = [['here', 'Where you are'], ['home', 'Home']].map((p) => {
    const on = st.place === p[0];
    return { name: p[1], pick: () => app.setState({ place: p[0] }), bg: on ? '#0f172a' : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });

  const TOUR = D.tour;
  const tourOn = st.tour >= 0 && sc === 'home';
  const tourStep = tourOn ? TOUR[st.tour] : ['', ''];
  const free = sw(st.free), off = sw(st.offline), fresh = sw(st.fresh), rain = sw(st.rain);

  return {
    agent: {},
    sheets: {},
    titles: { weather: D.weatherTitle },
    values: {
      designs,
      hours: D.hours.map((h) => ({ t: h[0], deg: h[1], rain: h[2] || ' ' })),
      toggleRain: () => app.setState((x) => ({ rain: !x.rain })), rainBg: rain.bg, rainJust: rain.just,
      featRows, featCount: featCount + ' of ' + FEAT.length + ' on', mapsKey: st.feat.driving && st.feat.travel && st.feat.calendar,
      voiceGroups, placeChips, allOn: () => say('Everything is on'),
      tourOn, tourTitle: tourStep[0], tourText: tourStep[1], tourCount: (st.tour + 1) + ' of ' + TOUR.length, tourNextLabel: st.tour === TOUR.length - 1 ? 'Done' : 'Next',
      tourNext: () => app.setState((x) => ({ tour: x.tour + 1 >= TOUR.length ? -1 : x.tour + 1 })), tourBack: () => app.setState((x) => ({ tour: Math.max(0, x.tour - 1) })), tourClose: () => app.setState({ tour: -1 }),
      pieces: D.pieces.map((p) => ({ n: p[0], t: p[1], done: p[2], start: () => app.setState({ screen: 'home', stack: [], tour: 0 }) })),
      demoMode: !!app.demoMode,
      offline: st.offline, free: st.free, fresh: st.fresh, notFresh: !st.fresh,
      goOnline: () => app.setState({ offline: false }),
      toggleFree: () => app.setState((x) => ({ free: !x.free })), freeBg: free.bg, freeJust: free.just,
      toggleOffline: () => app.setState((x) => ({ offline: !x.offline })), offBg: off.bg, offJust: off.just,
      toggleFresh: () => app.setState((x) => ({ fresh: !x.fresh })), freshBg: fresh.bg, freshJust: fresh.just,
      ringMe: () => app.setState({ incoming: true })
    }
  };
}
