// The call area: the call mode (it stays on wherever you go), the live transcript of the
// call, the mini bar, an incoming call, bring someone in, take that back, call me back,
// voice off, the demo-call and call-line-down banners. Texts with an agent are not here.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/call.js';

export const NAME = 'call';
export const WIRED = false;
export { demo };

export const start = {
  onCall: false, callAgent: 'donna', phase: 0, confirmHang: false, muted: false,
  yes: null, voiceOn: true, second: null, takenBack: false, incoming: false, demo: false
};

const PHASES = ['Calling…', 'Your turn', 'Listening…', 'Thinking…', 'Speaking'];
const RINGS = [4, 6, 18, 10, 26];
const ORDER = ['donna', 'pepper', 'mp'];

// Installed on the app: start a call with an agent, from wherever you are.
export const methods = {
  startCall(a) {
    this.setState((st) => ({
      onCall: true, callAgent: a, phase: 0, confirmHang: false, muted: false, yes: null, second: null, takenBack: false, incoming: false, demo: false,
      screen: 'call', stack: st.screen === 'call' ? st.stack : st.stack.concat([st.screen])
    }));
  }
};

const toLines = (arr, ag) => arr.map((b) => (b[0] === 'm'
  ? { who: 'You', t: b[1], nc: '#15803d', fc: '#0f172a', fs: '16px', fw: '500' }
  : (b[0] === 'w' ? { who: ag.name, t: b[1], nc: ag.accent, fc: '#64748b', fs: '14px', fw: '400' } : { who: ag.name, t: b[1], nc: ag.accent, fc: '#0f172a', fs: '16px', fw: '400' })));

export function vals(st, ctx, D) {
  const { app, AG, sc } = ctx;
  const say = (t) => app.say(t);
  const ca = AG[st.callAgent];
  const showMini = st.onCall && sc !== 'call' && sc !== 'transcript';
  const call = {
    donna: () => app.startCall('donna'), pepper: () => app.startCall('pepper'), mp: () => app.startCall('mp'),
    space: () => app.startCall(st.space), chat: () => app.startCall(st.chatAgent), textTo: () => app.startCall(st.textTo)
  };
  // What was said on the call (the live transcript)
  let tLines = toLines(D.callLines[st.callAgent], ca);
  if (st.callAgent === D.askOf && st.yes) tLines = tLines.concat(toLines(D.answers[st.yes], ca));
  const sec = st.second ? AG[st.second] : null;
  const tl2 = tLines.map((l) => Object.assign({ deco: 'none' }, l));
  if (st.takenBack) { for (let i = tl2.length - 1; i >= 0; i--) { if (tl2[i].who === 'You') { tl2[i] = Object.assign({}, tl2[i], { deco: 'line-through', fc: '#94a3b8' }); break; } } }
  if (sec) tl2.push({ who: sec.name, t: sec.name + ' picked up and is listening in.', nc: sec.accent, fc: sec.accent, fs: '14px', fw: '600', deco: 'none' });
  const sheets = {
    add: { title: 'Bring someone into the call', rows: ORDER.filter((k) => k !== st.callAgent).map((k) => ({ a: AG[k].name, b: AG[k].role, pick: () => { app.setState({ second: k, sheet: null }); say(AG[k].name + ' picked up'); } })) }
  };
  return {
    sheets,
    values: {
      call, chat: { call: () => app.go('transcript') }, ca, phase: PHASES[st.phase], ring: RINGS[st.phase],
      showMini, padCls: showMini ? 'pt' : '', chatTop: showMini ? '12px' : '52px',
      cyclePhase: () => app.setState((x) => ({ phase: (x.phase + 1) % 5 })),
      toggleMute: () => app.setState((x) => ({ muted: !x.muted })), muteLabel: st.muted ? 'Muted: she can’t hear you' : 'Mute',
      muteBg: st.muted ? '#fef3c7' : '#ffffff', muteFg: st.muted ? '#78350f' : '#0f172a', muteShort: st.muted ? 'Muted' : 'Mute',
      askHang: () => app.setState({ confirmHang: true }), stayOn: () => app.setState({ confirmHang: false }),
      hangUp: () => app.setState((x) => { const stack = x.stack.slice(); const prev = stack.length ? stack.pop() : 'home'; return { onCall: false, confirmHang: false, screen: prev, stack }; }),
      hangFromT: () => app.setState((x) => { const stack = x.stack.slice(); stack.pop(); return { screen: 'call', stack, confirmHang: true }; }),
      confirmHang: st.confirmHang,
      tLines: tl2, askOpen: st.callAgent === D.askOf && !st.yes,
      sayYes: () => app.setState({ yes: 'yes' }), sayNo: () => app.setState({ yes: 'no' }),
      callBg: sec ? 'linear-gradient(135deg, ' + ca.tint + ' 50%, ' + sec.tint + ' 50%)' : ca.tint,
      callTitle: sec ? ca.name + ' and ' + sec.name : ca.name, hasSecond: !!sec, sec: sec || ca,
      takeBack: () => { app.setState({ takenBack: true }); say('Taken back. She won’t act on your last line'); },
      callMeBack: () => { app.setState({ phase: 0 }); say(ca.name + ' hangs up and calls you straight back'); },
      toggleVoice: () => app.setState((x) => ({ voiceOn: !x.voiceOn })), voiceLabel: st.voiceOn ? 'Voice off' : 'Voice on',
      sheetAdd: () => app.setState({ sheet: 'add' }),
      demoOn: st.demo && sc === 'call', callErr: st.offline && sc === 'call',
      demoCall: { donna: () => { app.startCall('donna'); app.setState({ demo: true, tour: -1 }); }, pepper: () => { app.startCall('pepper'); app.setState({ demo: true }); } },
      incoming: st.incoming, pickUp: () => { app.setState({ incoming: false }); app.startCall('donna'); }, decline: () => { app.setState({ incoming: false }); say('Donna will text you instead'); }
    }
  };
}
