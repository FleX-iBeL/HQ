// Engine tests, run in a browser by web/tests.html. Each test mounts a small template in
// a scratch container, renders, changes state, renders again, and checks the live DOM.
import { compile, mount, DCLogic } from '../engine.js';

const tests = [];
const test = (name, fn) => tests.push({ name, fn });
const eq = (a, b, what) => { if (a !== b) throw new Error((what || 'value') + ': expected ' + JSON.stringify(b) + ', got ' + JSON.stringify(a)); };
const ok = (c, what) => { if (!c) throw new Error(what || 'expected true'); };

// A component whose renderVals is given; state merges at once, app.flush() renders now.
function setup(html, vals, state, opts) {
  const box = document.createElement('div');
  document.getElementById('scratch').appendChild(box);
  class C extends DCLogic { constructor() { super(); this.state = state || {}; } renderVals() { return vals(this.state, this); } }
  const c = new C();
  const app = mount(box, html, c, opts);
  return { box, c, app, set(p) { c.setState(p); app.flush(); } };
}

test('holes: text, interpolated and whole attributes, literals', () => {
  const { box, set } = setup('<p class="a {{ cls }} b" data-n="{{ n }}" title="{{ \'hi\' }}">{{ user.name }} · {{ missing.x }}|{{ true }}|{{ 7 }}</p>',
    (st) => ({ cls: st.cls, n: 3, user: { name: st.name } }), { cls: 'x', name: 'Ann' });
  const p = box.querySelector('p');
  eq(p.className, 'a x b', 'class'); eq(p.getAttribute('data-n'), '3', 'whole number'); eq(p.getAttribute('title'), 'hi', 'quoted literal');
  eq(p.textContent, 'Ann · ||7', 'text');
  set({ name: 'Bo', cls: 'y' });
  eq(p.textContent, 'Bo · ||7', 'text after'); eq(p.className, 'a y b', 'class after'); ok(box.querySelector('p') === p, 'same node');
});

test('entities in static text and attributes are decoded once', () => {
  const { box } = setup('<a title="Tom &amp; Jerry">Fish &amp; chips &lt;3 {{ v }}</a>', () => ({ v: '&amp;' }));
  const a = box.querySelector('a');
  eq(a.title, 'Tom & Jerry'); eq(a.textContent, 'Fish & chips <3 &amp;');
});

test('nested sc-for and sc-if, $index, a loop name that shadows an outer one', () => {
  const html = '<ul><sc-for list="{{ groups }}" as="g"><li data-i="{{ $index }}">{{ g.name }}:<sc-for list="{{ g.items }}" as="g"><b>{{ $index }}{{ g.t }}</b><sc-if value="{{ g.hot }}"><i>!</i></sc-if></sc-for></li></sc-for></ul><sc-if value="{{ none }}"><em>no</em></sc-if>';
  const { box, set } = setup(html, (st) => ({ groups: st.groups, none: false }), { groups: [{ name: 'A', items: [{ t: 'x', hot: true }, { t: 'y' }] }, { name: 'B', items: [] }] });
  const lis = box.querySelectorAll('li');
  eq(lis.length, 2, 'outer'); eq(lis[0].dataset.i, '0'); eq(lis[1].dataset.i, '1');
  eq(lis[0].textContent, 'A:0x!1y', 'inner with shadowing and $index'); eq(lis[1].textContent, 'B:', 'empty inner');
  ok(!box.querySelector('em'), 'false sc-if not drawn');
  set({ groups: [{ name: 'A', items: [{ t: 'x' }] }] });
  eq(box.querySelectorAll('li').length, 1, 'outer after'); eq(box.querySelectorAll('i').length, 0, 'inner sc-if gone');
});

test('a click handler fires once per click after many re-renders', () => {
  let n = 0;
  const { box, set } = setup('<button onClick="{{ hit }}">{{ c }}</button>', (st) => ({ c: st.c, hit: () => { n++; } }), { c: 0 });
  for (let i = 1; i <= 50; i++) set({ c: i });
  box.querySelector('button').click();
  eq(n, 1, 'calls');
  box.querySelector('button').click();
  eq(n, 2, 'calls after a second click');
});

test('the newest handler is the one that runs', () => {
  const seen = [];
  const { box, set } = setup('<button onClick="{{ hit }}">x</button>', (st) => ({ hit: () => seen.push(st.v) }), { v: 'a' });
  set({ v: 'b' });
  box.querySelector('button').click();
  eq(seen.join(), 'b');
});

test('an input keeps focus, caret and typed text while state changes around it', () => {
  const html = '<div><sc-if value="{{ banner }}"><p>banner</p></sc-if><span>{{ clock }}</span><input id="t" placeholder="Type {{ who }}"><sc-for list="{{ rows }}" as="r"><i>{{ r }}</i></sc-for></div>';
  const { box, set } = setup(html, (st) => st, { banner: false, clock: 0, who: 'Donna', rows: [] });
  const input = box.querySelector('#t');
  input.focus(); input.value = 'hello there'; input.setSelectionRange(5, 5);
  set({ banner: true, clock: 1, rows: ['a', 'b'] });
  set({ banner: false, clock: 2, who: 'Pepper', rows: ['b'] });
  ok(box.querySelector('#t') === input, 'same input node');
  ok(document.activeElement === input, 'still focused');
  eq(input.value, 'hello there', 'typed text'); eq(input.selectionStart, 5, 'caret');
  eq(input.placeholder, 'Type Pepper', 'its attribute still updates');
});

test('value="{{ x }}" stays in step without fighting the typing; onInput updates state', () => {
  const { box, c, app } = setup('<input value="{{ text }}" onInput="{{ typed }}"><span>{{ text }}</span>',
    (st, comp) => ({ text: st.text, typed: (e) => comp.setState({ text: e.target.value }) }), { text: 'ab' });
  const input = box.querySelector('input');
  eq(input.value, 'ab', 'first value');
  input.focus(); input.value = 'abc'; input.setSelectionRange(1, 1);
  input.dispatchEvent(new Event('input', { bubbles: true }));
  app.flush();
  eq(c.state.text, 'abc', 'state from typing'); eq(box.querySelector('span').textContent, 'abc');
  eq(input.selectionStart, 1, 'caret kept');
  input.value = 'abcd'; app.flush();
  eq(input.value, 'abcd', 'a re-render with the same state leaves the typed text');
  c.setState({ text: '' }); app.flush();
  eq(input.value, '', 'state cleared from code clears the field');
});

test('onKeyDown, onChange and onSubmit (which stops the browser submit)', () => {
  const got = [];
  const { box } = setup('<form onSubmit="{{ sub }}"><input onKeyDown="{{ key }}" onChange="{{ ch }}"><button>go</button></form>',
    () => ({ sub: (e) => got.push('submit:' + e.defaultPrevented), key: (e) => got.push('key:' + e.key), ch: () => got.push('change') }));
  const input = box.querySelector('input');
  input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
  input.dispatchEvent(new Event('change', { bubbles: true }));
  box.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  eq(got.join(), 'key:Enter,change,submit:true');
});

test('a keyed list keeps each item\'s node when re-ordered', () => {
  const html = '<ul><sc-for list="{{ xs }}" as="x"><li key="{{ x.id }}">{{ x.t }}</li></sc-for></ul>';
  const { box, set } = setup(html, (st) => st, { xs: [{ id: 1, t: 'one' }, { id: 2, t: 'two' }, { id: 3, t: 'three' }] });
  const before = [...box.querySelectorAll('li')];
  set({ xs: [{ id: 3, t: 'three' }, { id: 1, t: 'one!' }, { id: 2, t: 'two' }] });
  const after = [...box.querySelectorAll('li')];
  ok(after[0] === before[2] && after[1] === before[0] && after[2] === before[1], 'nodes followed their keys');
  eq(after.map((l) => l.textContent).join(), 'three,one!,two');
  set({ xs: [{ id: 2, t: 'two' }] });
  ok(box.querySelector('li') === before[1], 'the kept one is the same node');
});

test('without a key, list items follow their place', () => {
  const { box, set } = setup('<ul><sc-for list="{{ xs }}" as="x"><li>{{ x }}</li></sc-for></ul>', (st) => st, { xs: ['a', 'b'] });
  const first = box.querySelector('li');
  set({ xs: ['b', 'a', 'c'] });
  ok(box.querySelector('li') === first, 'place 0 kept its node'); eq(box.querySelector('ul').textContent, 'bac');
});

test('inline SVG: namespace, viewBox and dashed attribute names come through', () => {
  const html = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="{{ c }}" stroke-width="2" stroke-linecap="round" aria-hidden="true"><sc-if value="{{ on }}"><path d="M9 18l6-6-6-6"></path></sc-if><circle cx="12" cy="12" r="10"></circle></svg>';
  const { box, set } = setup(html, (st) => st, { c: 'red', on: true });
  const svg = box.querySelector('svg');
  eq(svg.namespaceURI, 'http://www.w3.org/2000/svg', 'svg ns'); eq(svg.getAttribute('viewBox'), '0 0 24 24', 'viewBox');
  eq(svg.viewBox.baseVal.width, 24, 'viewBox parsed'); eq(svg.getAttribute('stroke-linecap'), 'round');
  eq(box.querySelector('path').namespaceURI, 'http://www.w3.org/2000/svg', 'path ns (inside sc-if)');
  eq(box.querySelector('circle').namespaceURI, 'http://www.w3.org/2000/svg', 'circle ns');
  set({ c: 'blue', on: false });
  eq(svg.getAttribute('stroke'), 'blue'); ok(!box.querySelector('path'), 'path removed');
});

test('boolean, aria and data attributes', () => {
  const { box, set } = setup('<button disabled="{{ off }}" aria-pressed="{{ on }}" data-x="{{ on }}" aria-checked="{{ str }}">b</button>', (st) => st, { off: true, on: false, str: 'true' });
  const b = box.querySelector('button');
  ok(b.disabled, 'disabled'); eq(b.getAttribute('aria-pressed'), 'false'); eq(b.getAttribute('data-x'), 'false'); eq(b.getAttribute('aria-checked'), 'true');
  set({ off: false, on: true });
  ok(!b.hasAttribute('disabled'), 'disabled removed'); eq(b.getAttribute('aria-pressed'), 'true');
});

test('style strings are kept as written', () => {
  const { box, set } = setup('<div style="width: 44px; background: {{ bg }}">x</div>', (st) => st, { bg: '#fff' });
  const d = box.querySelector('div');
  eq(d.getAttribute('style'), 'width: 44px; background: #fff');
  set({ bg: '#000' });
  eq(d.style.background.replace(/\s/g, ''), 'rgb(0,0,0)');
});

test('removed nodes go, and a removed listener no longer fires', () => {
  let n = 0;
  const { box, set } = setup('<sc-if value="{{ show }}"><button id="a" onClick="{{ hit }}">a</button></sc-if><button id="b" onClick="{{ maybe }}">b</button>',
    (st) => ({ show: st.show, hit: () => n++, maybe: st.wire ? () => n++ : null }), { show: true, wire: true });
  const a = box.querySelector('#a'), b = box.querySelector('#b');
  set({ show: false, wire: false });
  ok(!a.isConnected, 'node removed'); ok(!box.querySelector('#a'), 'not in the DOM');
  a.click(); b.click();
  eq(n, 0, 'no handler ran'); ok(box.querySelector('#b') === b, 'b reused');
});

test('ref: a function gets the node, and null when it goes; an object gets .current', () => {
  const seen = []; const obj = { current: null };
  const { box, set } = setup('<sc-if value="{{ show }}"><input ref="{{ r }}"></sc-if><p ref="{{ o }}">p</p>', (st) => ({ show: st.show, r: st.fn, o: obj }), { show: true, fn: (el) => seen.push(el ? el.tagName : null) });
  eq(seen.join(), 'INPUT'); ok(obj.current === box.querySelector('p'), 'object ref');
  set({ show: false });
  eq(seen.join(), 'INPUT,', 'called with null after removal');
});

test('a scrolled panel keeps its scroll position through a re-render', () => {
  const { box, set } = setup('<div id="s" style="height: 50px; overflow-y: auto"><sc-for list="{{ xs }}" as="x"><p style="height: 30px; margin: 0">{{ x }} {{ n }}</p></sc-for></div>', (st) => st, { xs: [1, 2, 3, 4, 5, 6, 7, 8], n: 0 });
  const s = box.querySelector('#s');
  s.scrollTop = 90;
  set({ n: 1 });
  ok(box.querySelector('#s') === s, 'same node'); eq(s.scrollTop, 90, 'scroll kept');
});

test('setState batches to one render on the next frame', async () => {
  let renders = 0;
  const box = document.createElement('div'); document.getElementById('scratch').appendChild(box);
  class C extends DCLogic { constructor() { super(); this.state = { a: 0 }; } renderVals() { renders++; return { a: this.state.a }; } }
  const c = new C();
  mount(box, '<b>{{ a }}</b>', c);
  c.setState({ a: 1 }); c.setState((s) => ({ a: s.a + 1 })); c.setState({ b: 1 });
  eq(renders, 1, 'not yet'); eq(c.state.a, 2, 'state merged at once');
  await new Promise((r) => setTimeout(r, 150));
  eq(renders, 2, 'one render'); eq(box.textContent, '2');
});

test('hq-include is replaced by its template at compile time', () => {
  const tpl = compile('<main><hq-include name="one"></hq-include><hq-include name="two"></hq-include></main>', { include: (n) => (n === 'one' ? '<b>{{ a }}</b>' : '<i>two</i>') });
  const box = document.createElement('div'); document.getElementById('scratch').appendChild(box);
  class C extends DCLogic { renderVals() { return { a: 'A' }; } }
  mount(box, tpl, new C());
  eq(box.querySelector('main').innerHTML, '<b>A</b><i>two</i>');
});

test('hint-* attributes are dropped; a handler error goes to onError with its name', () => {
  const errs = [];
  const { box } = setup('<sc-if value="{{ t }}" hint-placeholder-val="{{ true }}"><button hint-x="1" onClick="{{ boom }}">x</button></sc-if>',
    () => ({ t: true, boom: () => { throw new Error('bang'); } }), {}, { onError: (e, w) => errs.push(w.handler + ':' + e.message) });
  const b = box.querySelector('button');
  ok(!b.hasAttribute('hint-x'), 'hint dropped');
  b.click();
  eq(errs.join(), 'boom:bang');
});

export async function run(out) {
  let pass = 0, fail = 0;
  for (const t of tests) {
    try { await t.fn(); pass++; out(true, t.name); } catch (e) { fail++; out(false, t.name + ': ' + e.message); }
  }
  document.getElementById('scratch').textContent = '';
  return { pass, fail };
}
