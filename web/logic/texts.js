// The texts area: the chat (texts) with each agent, who you text from home, the list of the
// three chats, the bell (her texts on or off), a failed text and Try again, past calls and
// reading one. The live transcript of a call is the call area's, not this one.
// Conventions: see ../WIRING.md. vals(st, ctx, D): D is the demo module or the real data.
import * as demo from './demo/texts.js';

export const NAME = 'texts';
export const WIRED = false;
export { demo };

export const start = { chatAgent: 'donna', textTo: 'donna', logAgent: 'donna', textsOn: false, retried: false };

const ORDER = ['donna', 'pepper', 'mp'];
const toBubbles = (arr, ag) => arr.map((b) => (b[0] === 'm'
  ? { t: b[1], align: 'flex-end', bg: '#22c55e', fg: '#052e16', radius: '20px 20px 6px 20px' }
  : { t: b[1], align: 'flex-start', bg: ag.tint, fg: '#0f172a', radius: '20px 20px 20px 6px' }));
const toLines = (arr, ag) => arr.map((b) => (b[0] === 'm'
  ? { who: 'You', t: b[1], nc: '#15803d', fc: '#0f172a', fs: '16px', fw: '500' }
  : { who: ag.name, t: b[1], nc: ag.accent, fc: '#0f172a', fs: '16px', fw: '400' }));

export function vals(st, ctx, D) {
  const { app, AG, sa } = ctx;
  const say = (t) => app.say(t);
  const cha = AG[st.chatAgent];
  const textChips = ORDER.map((k) => {
    const on = st.textTo === k;
    return { name: AG[k].name, on: on ? 'true' : 'false', pick: () => app.setState({ textTo: k }),
      bg: on ? AG[k].color : '#ffffff', fg: on ? AG[k].ink : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' };
  });
  const pastCalls = D.pastCalls[st.space].map((d) => ({ day: d.day, items: d.items.map((c) => ({ time: c[0], about: c[1], lines: c[2], open: () => app.go('callLog') })) }));
  const chatList = ORDER.map((k) => {
    const arr = D.texts[k]; const last = arr[arr.length - 1]; const cur = st.space === k; const unread = D.unread[k];
    return { name: AG[k].name, initial: AG[k].initial, color: AG[k].color, ink: AG[k].ink, accent: AG[k].accent, preview: last[1], time: D.lastText[k],
      tc: unread ? AG[k].accent : '#55555c', unread, hasUnread: unread > 0, current: cur ? 'true' : 'false',
      bg: cur ? AG[k].color : 'transparent', fg: cur ? AG[k].ink : '#111114', faceBg: cur ? '#ffffff' : AG[k].color, faceFg: cur ? AG[k].color : AG[k].ink,
      open: () => app.go(k, { space: k }), call: () => app.startCall(k) };
  });
  return {
    agent: { donna: { rows: D.rows } },
    values: {
      // `chat` is shared with the call area, which adds chat.call (the live transcript)
      chat: { space: () => app.go('chat', { chatAgent: st.space }), textTo: () => app.go('chat', { chatAgent: st.textTo }) },
      cha, tt: AG[st.textTo], textChips,
      bubbles: toBubbles(D.texts[st.chatAgent], cha), spaceBubbles: toBubbles(D.texts[st.space], sa), chatList,
      textsOff: !st.textsOn, toggleTexts: () => app.setState((x) => ({ textsOn: !x.textsOn })),
      bellBtnBg: st.textsOn ? cha.tint : '#ffffff', bellBtnFg: st.textsOn ? cha.accent : '#0f172a', bellAria: st.textsOn ? 'Her texts are on. Turn them off' : 'Turn her texts on',
      showFailed: st.chatAgent === D.failedIn && !st.retried, retry: () => { app.setState({ retried: true }); say('Sent'); },
      pastCalls, logBubbles: toLines(D.pastCallLog, sa)
    }
  };
}
