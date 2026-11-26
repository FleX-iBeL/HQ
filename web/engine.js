/*
 * engine.js: HQ's own small template engine. No dependencies, no build step.
 *
 * Templates are HTML text with:
 *   {{ a.b.c }}            a dotted lookup (also {{ $index }} and the literals true,
 *                          false, null, numbers and 'quoted' strings); never an expression
 *   x="{{ path }}"         the whole value: the raw value (a function, a number, a ref)
 *   x="a {{ p }} b"        an interpolated string
 *   <sc-if value="{{ c }}">            shown when c is truthy
 *   <sc-for list="{{ xs }}" as="x">    repeated per item, with x and $index in scope;
 *                                      loops nest, and an inner name shadows an outer one
 *   key="{{ x.id }}"       on the first element inside an sc-for: the item's identity, so a
 *                          re-ordered list keeps its nodes (without it, the index is used)
 *   onClick="{{ fn }}"     any camelCase on* attribute is a real listener (onClick, onInput,
 *                          onChange, onKeyDown, onSubmit, ...); one listener per node and
 *                          event, the handler swapped on each render; onSubmit also stops
 *                          the browser's own form submit
 *   value="{{ x }}"        on input / textarea / select: set as the property, and only when
 *                          the value given changed since the last render, so it never
 *                          fights what the person is typing; checked and selected likewise
 *   ref="{{ r }}"          a function called with the node (and with null once it's gone),
 *                          or an object whose .current is set
 *   <hq-include name="n"></hq-include>  replaced at compile time by opts.include(n)
 *   class, style strings, boolean attributes (true sets it, false / null removes it),
 *   aria-* and data-* (booleans written as "true" / "false"), inline SVG in its namespace
 *   with its attribute names as written (viewBox, stroke-linecap, ...).
 * hint-* attributes are ignored.
 * A hole that is the whole text of its node and holds rich(text) is drawn as formatted text
 * (bold, italics, lists, line breaks, links), built as nodes; see rich() below.
 *
 * Rendering morphs the live DOM: a node is reused when the same place in the template
 * (and the same loop item) renders the same tag again, attributes and text are updated
 * in place, and only what is gone is removed, so focus, caret, typed text and scroll
 * positions survive a re-render.
 *
 * DCLogic is the base class of a component: state, setState(objOrFn) (merged at once,
 * rendered on the next frame), forceUpdate(), componentDidMount(), props, renderVals().
 */

const SVG_NS = 'http://www.w3.org/2000/svg';
const VOID = new Set(['area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr']);
const TAG = /<!--[\s\S]*?-->|<(\/?)([a-zA-Z][\w-]*)((?:[^>"']|"[^"]*"|'[^']*')*?)(\/?)>/g;
const ATTR = /([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g;
const HOLE = /\{\{\s*([^}]*?)\s*\}\}/g;
const WHOLE = /^\{\{\s*([^}]*?)\s*\}\}$/;
const PROPS = new Set(['value', 'checked', 'selected']);

/* The style lens: when set, every style attribute value goes through it before it is
 * compared and written, so a theme can rewrite colours in inline styles. Results are
 * memoised per input string until the lens changes. */
let styleLens = null;
let lensMemo = new Map();
const mounted = new Set();
function lensed(v) {
  if (!styleLens || typeof v !== 'string' || !v) return v;
  let out = lensMemo.get(v);
  if (out === undefined) {
    try { out = styleLens(v); } catch (err) { console.error(err); out = v; }
    if (typeof out !== 'string') out = v;
    if (lensMemo.size > 5000) lensMemo.clear();
    lensMemo.set(v, out);
  }
  return out;
}
/* setStyleLens(fn) sets the lens (null clears it). It does not re-render by itself:
 * call rerenderAll() after it (app.flush() and forceUpdate() do not: flush only renders
 * when a frame is pending, and forceUpdate schedules a render of one component). */
export function setStyleLens(fn) {
  styleLens = typeof fn === 'function' ? fn : null;
  lensMemo = new Map();
}
/* rerenderAll() renders every mounted app now, so a changed lens reaches every node.
 * Only attributes whose lensed value changed are rewritten. */
/* typedIn(node): the person typed in this input; what it holds now counts as the value last
 * rendered, so a draft kept outside the render (no re-render per keystroke) is not written
 * back, and a later render that clears the draft does clear the box. */
export function typedIn(node) {
  if (!node || !('value' in node)) return;
  node.__a = Object.assign({}, node.__a || {}, { value: node.value });
}
export function rerenderAll() { for (const r of [...mounted]) r(); }
/* holdRenders(): scheduled renders (setState, forceUpdate) wait until the returned release() is
 * called, then one render runs if any was asked. For a drag or a gesture, so nothing re-renders
 * the nodes under the finger. A direct render() or rerenderAll() still runs. Holds nest. */
let holds = 0;
const waiting = new Set();
export function holdRenders() {
  holds++;
  let done = false;
  return () => {
    if (done) return; done = true;
    if (--holds > 0) return;
    const list = [...waiting]; waiting.clear();
    for (const sched of list) sched();
  };
}

let decoder = null;
function decode(s) {
  if (s.indexOf('&') < 0) return s;
  if (!decoder) decoder = document.createElement('textarea');
  decoder.innerHTML = s;
  return decoder.value;
}

/* A hole's text into a function of the scope. */
function lookup(src) {
  if (src === 'true') return () => true;
  if (src === 'false') return () => false;
  if (src === 'null') return () => null;
  if (src === 'undefined' || src === '') return () => undefined;
  if (/^-?\d+(\.\d+)?$/.test(src)) { const n = Number(src); return () => n; }
  if (/^'.*'$|^".*"$/.test(src)) { const t = src.slice(1, -1); return () => t; }
  const path = src.split('.');
  return (scope) => {
    let v = scope[path[0]];
    for (let i = 1; i < path.length && v != null; i++) v = v[path[i]];
    return v;
  };
}

/* Static text and holes, as parts: strings and functions. */
function parts(text) {
  const out = [];
  let last = 0, m;
  HOLE.lastIndex = 0;
  while ((m = HOLE.exec(text))) {
    if (m.index > last) out.push(decode(text.slice(last, m.index)));
    out.push(lookup(m[1]));
    last = HOLE.lastIndex;
  }
  if (last < text.length) out.push(decode(text.slice(last)));
  return out;
}
const show = (v) => (v == null || v === false || v === true ? '' : String(v));

/* ---------------------------------------------------------------- rich text
 * rich(text, opts) makes a value that a hole standing alone in a text node ({{ l.t }} as the
 * whole text of its element) draws as formatted text, built as nodes (never as HTML):
 *   **bold**, *italics*, lines starting with "- ", "* ", "• " or "1. " as a list (an indented item
 *   is a list inside the item above, two levels deep at most; an indented plain line goes on with
 *   that item), paragraphs and line breaks kept, a line like --- only a break, a heading shown as a
 *   bold line, and web addresses (http, https, www.) and [words](https://…) as links that open
 *   outside the app (a new tab or the browser), so a call goes on.
 * opts.marks false: only links and line breaks (his own lines). opts.at: a small time at the end,
 * in the corner of the bubble. Anywhere else (an attribute, a hole among other text) the value is
 * its plain text, without the marks. */
export class Rich {
  constructor(text, opts) {
    this.text = String(text == null ? '' : text);
    this.marks = !(opts && opts.marks === false);
    this.at = (opts && opts.at) || '';
  }
  toString() { return this.marks ? plainOf(this.text) : this.text.replace(LINK_RE, (m, w, u) => w || m); }
}
export const rich = (text, opts) => new Rich(text, opts);

const LINK_RE = /\[([^\]\n]+)\]\((https?:\/\/[^\s)]+)\)|((?:https?:\/\/|\bwww\.)[^\s<>"]*[^\s<>".,;:!?)\]'*])/gi;
const LINK_STYLE = 'color: inherit; text-decoration: underline; text-underline-offset: 2px; overflow-wrap: anywhere';
function plainOf(s) {
  return String(s || '').replace(LINK_RE, (m, w, u) => w || m).replace(/\*\*(.+?)\*\*/g, '$1')
    .replace(/(^|[\s(])\*([^*\s](?:[^*]*[^*\s])?)\*(?=[\s).,!?:;]|$)/g, '$1$2').replace(/^#{1,6}\s+/gm, '');
}
// A tree of plain objects: a string is text, {tag, kids, href, start} an element.
function linkParts(s, out) {
  let at = 0;
  LINK_RE.lastIndex = 0;
  for (const m of s.matchAll(LINK_RE)) {
    if (m.index > at) out.push(s.slice(at, m.index));
    const url = m[2] || m[3];
    const href = /^www\./i.test(url) ? 'https://' + url : url;
    if (/^https?:\/\//i.test(href)) out.push({ tag: 'a', href, kids: [m[1] || url] });
    else out.push(m[0]);
    at = m.index + m[0].length;
  }
  if (at < s.length) out.push(s.slice(at));
}
function inlineParts(s, out) {
  const ps = s.split(/\*\*(.+?)\*\*|\*([^*\s](?:[^*]*[^*\s])?)\*/g);
  for (let i = 0; i < ps.length; i += 3) {
    if (ps[i]) linkParts(ps[i].replace(/\*\*/g, ''), out);
    const b = ps[i + 1], it = ps[i + 2];
    if (b || it) { const e = { tag: b ? 'strong' : 'em', kids: [] }; linkParts(b || it, e.kids); out.push(e); }
  }
}
function parseRich(text, marks) {
  const src = String(text || '').replace(/\r/g, '');
  if (!marks) {
    const out = [];
    src.split('\n').forEach((ln, i) => { if (i) out.push({ tag: 'br', kids: [] }); linkParts(ln, out); });
    return out;
  }
  const root = [];
  let lists = [], para = null; // lists: the open lists, outermost first, each {list, indent, li, into}
  for (const raw of src.split('\n')) {
    const indent = raw.match(/^[ \t]*/)[0].replace(/\t/g, '    ').length;
    const line = raw.trim();
    if (/^([-*_])(?:\s*\1){2,}$/.test(line)) { lists = []; para = null; continue; }
    const m = line.match(/^(?:([-*+•])|(\d{1,3})[.)])\s+(.*)$/);
    if (m) {
      const tag = m[1] ? 'ul' : 'ol';
      while (lists.length > 1 && indent < lists[lists.length - 1].indent) lists.pop();
      let top = lists[lists.length - 1];
      const make = () => ({ tag, kids: [], start: tag === 'ol' && +m[2] !== 1 ? +m[2] : null });
      if (top && indent > top.indent && top.li && lists.length < 3) {
        const list = make(); list.nested = true;
        top.li.kids.push(list);
        lists.push(top = { list, indent, li: null, into: top.li.kids });
      } else if (!top || top.list.tag !== tag) {
        const list = make();
        const into = top ? top.into : root;
        if (top && top.list.nested) list.nested = true;
        into.push(list);
        top = { list, indent: top ? top.indent : indent, li: null, into };
        if (lists.length) lists[lists.length - 1] = top; else lists.push(top);
      }
      const li = { tag: 'li', kids: [] };
      inlineParts(m[3], li.kids);
      top.list.kids.push(li); top.li = li;
      para = null; continue;
    }
    if (!line) { para = null; continue; }
    const last = lists[lists.length - 1];
    if (last && last.li && indent > 0) { last.li.kids.push({ tag: 'br', kids: [] }); inlineParts(line, last.li.kids); continue; }
    lists = [];
    const head = line.match(/^#{1,6}\s+(.*)$/);
    if (head) {
      const e = { tag: 'strong', kids: [] }; inlineParts(head[1], e.kids);
      root.push({ tag: 'p', kids: [e] }); para = null; continue;
    }
    if (para) para.kids.push({ tag: 'br', kids: [] });
    else { para = { tag: 'p', kids: [] }; root.push(para); }
    inlineParts(line, para.kids);
  }
  // one paragraph: its words stand in the element itself, as plain text would
  return root.length === 1 && root[0].tag === 'p' ? root[0].kids : root;
}
let richMemo = new Map();
function richTree(r) {
  const key = (r.marks ? '1' : '0') + r.text;
  let t = richMemo.get(key);
  if (!t) {
    t = parseRich(r.text, r.marks);
    if (richMemo.size > 2000) richMemo = new Map();
    richMemo.set(key, t);
  }
  return t;
}
function styleOf(n, i, parentTag) {
  if (n.tag === 'a') return LINK_STYLE;
  if (n.tag === 'strong') return 'font-weight: 650';
  if (n.tag === 'p') return i ? 'margin: 0.65em 0 0' : 'margin: 0';
  if (n.tag === 'ul' || n.tag === 'ol') return 'margin: ' + (n.nested ? '0.35em' : i ? '0.65em' : '0') + ' 0 0; padding-left: 1.4em';
  if (n.tag === 'li') return 'padding-left: 0.15em' + (i ? '; margin-top: 0.35em' : '');
  return null;
}
function richVNodes(tree, base, out, parentTag) {
  let block = 0, item = 0;
  tree.forEach((n, j) => {
    const k = base + '.' + j;
    if (typeof n === 'string') { out.push({ k, text: n }); return; }
    const isBlock = n.tag === 'p' || n.tag === 'ul' || n.tag === 'ol';
    const i = n.tag === 'li' ? item++ : isBlock ? block++ : 0;
    const attrs = {};
    const st = styleOf(n, i, parentTag);
    if (st) attrs.style = styleLens ? lensed(st) : st;
    if (n.tag === 'a') { attrs.href = n.href; attrs.target = '_blank'; attrs.rel = 'noopener noreferrer'; }
    if (n.start) attrs.start = String(n.start);
    const v = { k: k + n.tag, name: n.tag, svg: false, attrs, on: {}, src: {}, kids: [] };
    richVNodes(n.kids, k, v.kids, n.tag);
    out.push(v);
  });
}
const AT_STYLE = 'float: right; margin: 6px 0 -4px 10px; font-size: 11px; line-height: 14px; font-weight: 400; opacity: 0.6; white-space: nowrap; font-variant-numeric: tabular-nums';
function richOut(r, base, out) {
  richVNodes(richTree(r), base + '~', out, null);
  if (r.at) out.push({ k: base + '~at', name: 'span', svg: false, attrs: { style: AT_STYLE, 'aria-label': 'at ' + r.at }, on: {}, src: {}, kids: [{ k: base + '~at.t', text: r.at }] });
}
const join = (ps, scope) => ps.map((p) => (typeof p === 'string' ? p : show(p(scope)))).join('');

/* compile(html, {include}) -> a template that render() understands. */
export function compile(html, opts = {}) {
  let id = 0;
  const root = { kids: [] };
  const stack = [root];
  const textNode = (t) => {
    if (!t) return;
    stack[stack.length - 1].kids.push({ type: 'text', id: id++, parts: parts(t) });
  };
  const tokens = (src) => {
    let last = 0, m;
    const re = new RegExp(TAG.source, 'g');
    while ((m = re.exec(src))) {
      textNode(src.slice(last, m.index));
      last = re.lastIndex;
      if (m[0].startsWith('<!--')) continue;
      const [, close, tag, attrText, self] = m;
      const name = tag.toLowerCase();
      if (close) {
        const top = stack.pop();
        if (!top || top.tag !== name) throw new Error('Template: </' + tag + '> closes <' + (top && top.tag) + '>');
        continue;
      }
      const attrs = {};
      let a;
      ATTR.lastIndex = 0;
      while ((a = ATTR.exec(attrText))) attrs[a[1]] = a[2] ?? a[3] ?? a[4] ?? '';
      if (name === 'hq-include') {
        if (!opts.include) throw new Error('Template: <hq-include> without an include function');
        tokens(opts.include(attrs.name));
        if (!self) stack.push({ tag: 'hq-include', kids: stack[stack.length - 1].kids, skip: true });
        continue;
      }
      const parent = stack[stack.length - 1];
      let node;
      const inSvg = !!parent.inSvg || name === 'svg';
      if (name === 'sc-if') node = { type: 'if', test: lookup((attrs.value || '').replace(WHOLE, '$1')), kids: [] };
      else if (name === 'sc-for') node = { type: 'for', list: lookup((attrs.list || '').replace(WHOLE, '$1')), as: attrs.as || 'item', kids: [] };
      else node = element(tag, attrs, inSvg);
      node.inSvg = inSvg && name !== 'foreignobject';
      node.tag = name;
      node.id = id++;
      parent.kids.push(node);
      if (!self && !VOID.has(name)) stack.push(node);
    }
    textNode(src.slice(last));
  };
  tokens(html);
  if (stack.length !== 1) throw new Error('Template: <' + stack[stack.length - 1].tag + '> is never closed');
  return { kids: root.kids };
}

function element(tag, attrs, svg) {
  const node = { type: 'el', name: svg ? tag : tag.toLowerCase(), svg, attrs: [], on: [], kids: [] };
  for (const k of Object.keys(attrs)) {
    if (k.startsWith('hint-')) continue;
    const raw = attrs[k];
    const whole = raw.match(WHOLE);
    if (/^on[A-Z]/.test(k)) {
      const ev = k.slice(2).toLowerCase();
      node.on.push({ ev: ev === 'doubleclick' ? 'dblclick' : ev, get: lookup(whole ? whole[1] : raw), src: whole ? whole[1] : raw });
    } else if (k === 'key') node.key = lookup(whole ? whole[1] : raw);
    else if (k === 'ref') node.ref = lookup(whole ? whole[1] : raw);
    else if (whole) node.attrs.push({ n: k, get: lookup(whole[1]) });
    else if (raw.indexOf('{{') >= 0) { const ps = parts(raw); node.attrs.push({ n: k, get: (s) => join(ps, s) }); }
    else { const v = decode(raw); node.attrs.push({ n: k, get: () => v }); }
  }
  return node;
}

/* The template and values into virtual nodes, each with k: its place in the template. */
function build(kids, scope, sfx, out) {
  for (const n of kids) {
    if (n.type === 'text') {
      if (n.parts.length === 1 && typeof n.parts[0] === 'function') {
        const v = n.parts[0](scope);
        if (v instanceof Rich) { richOut(v, n.id + sfx, out); continue; }
        out.push({ k: n.id + sfx, text: show(v) });
      } else out.push({ k: n.id + sfx, text: join(n.parts, scope) });
    }
    else if (n.type === 'if') { if (n.test(scope)) build(n.kids, scope, sfx, out); }
    else if (n.type === 'for') {
      const list = n.list(scope);
      if (!list || !list.length) continue;
      const first = n.kids.find((c) => c.type === 'el');
      for (let i = 0; i < list.length; i++) {
        const inner = Object.create(scope);
        inner[n.as] = list[i];
        inner.$index = i;
        const key = first && first.key ? first.key(inner) : undefined;
        build(n.kids, inner, sfx + '/' + n.id + (key == null ? ':' + i : '#' + key), out);
      }
    } else {
      const v = { k: n.id + sfx, name: n.name, svg: n.svg, attrs: {}, on: {}, src: {}, kids: [] };
      for (const a of n.attrs) {
        let x = a.get(scope);
        if (x instanceof Rich) x = String(x);
        v.attrs[a.n] = a.n === 'style' && styleLens ? lensed(x) : x;
      }
      for (const e of n.on) { const f = e.get(scope); if (typeof f === 'function') { v.on[e.ev] = f; v.src[e.ev] = e.src; } }
      if (n.ref) v.ref = n.ref(scope);
      build(n.kids, scope, sfx, v.kids);
      out.push(v);
    }
  }
  return out;
}

function dispatch(e) {
  const f = this.__on && this.__on[e.type];
  if (!f) return;
  if (e.type === 'submit') e.preventDefault();
  const host = this.__host;
  if (host && host.onError) {
    try { f.call(null, e); } catch (err) { host.onError(err, { event: e.type, handler: this.__src[e.type], node: this }); }
  } else f.call(null, e);
}

function setAttr(node, name, val, prev, first) {
  if (PROPS.has(name) && name in node) {
    if (first || val !== prev) {
      if (name === 'value') { const s = val == null ? '' : String(val); if (node.value !== s) node.value = s; }
      else node[name] = !!val;
    }
    return;
  }
  if (val == null || val === false) {
    if (/^(aria|data)-/.test(name) && val === false) node.setAttribute(name, 'false');
    else node.removeAttribute(name);
  } else if (val === true) node.setAttribute(name, /^(aria|data)-/.test(name) ? 'true' : '');
  else if (typeof val !== 'function' && typeof val !== 'object') node.setAttribute(name, String(val));
}

function create(v, host) {
  if (v.text !== undefined) { const t = document.createTextNode(v.text); t.__k = v.k; return t; }
  const node = v.svg ? document.createElementNS(SVG_NS, v.name) : document.createElement(v.name);
  node.__k = v.k;
  node.__host = host;
  update(node, v, host, true);
  return node;
}

function update(node, v, host, first) {
  if (v.text !== undefined) { if (node.data !== v.text) node.data = v.text; return; }
  const prev = node.__a || {};
  for (const name in v.attrs) if (first || prev[name] !== v.attrs[name]) setAttr(node, name, v.attrs[name], prev[name], first);
  for (const name in prev) if (!(name in v.attrs)) { if (PROPS.has(name) && name in node && name !== 'value') node[name] = false; node.removeAttribute(name); }
  node.__a = v.attrs;
  const had = node.__on || {};
  for (const ev in v.on) if (!had[ev]) node.addEventListener(ev, dispatch);
  for (const ev in had) if (!v.on[ev]) node.removeEventListener(ev, dispatch);
  // A node you press (a click or pointer handler) carries data-press, so the app's one style
  // rule keeps a held press from selecting its text or opening the phone's callout.
  const press = !!(v.on.click || v.on.pointerdown || v.on.mousedown || v.on.touchstart);
  if (press !== !!node.__press) { node.__press = press; if (press) node.setAttribute('data-press', ''); else node.removeAttribute('data-press'); }
  node.__on = v.on;
  node.__src = v.src;
  if (v.ref !== node.__ref) {
    if (node.__ref) setRef(node.__ref, null);
    node.__ref = v.ref;
    if (v.ref) { setRef(v.ref, node); host.refs.add(node); }
  }
  patch(node, v.kids, host);
}

function setRef(r, val) {
  if (typeof r === 'function') r(val);
  else if (r && typeof r === 'object') r.current = val;
}

function fits(node, v) {
  if (v.text !== undefined) return node.nodeType === 3;
  return node.nodeType === 1 && (v.svg ? node.namespaceURI === SVG_NS && node.localName === v.name
    : node.namespaceURI !== SVG_NS && node.localName === v.name);
}

/* A node leaves the DOM: its listeners go with it (also those of everything inside it). */
function retire(parent, node) {
  parent.removeChild(node);
  if (node.nodeType !== 1) return;
  for (const el of [node, ...node.querySelectorAll('*')]) {
    if (el.__on) { for (const ev in el.__on) el.removeEventListener(ev, dispatch); el.__on = null; }
  }
}

/* Make parent's children match the virtual list, reusing nodes by their place. */
function patch(parent, vkids, host) {
  const old = new Map();
  for (let c = parent.firstChild; c; c = c.nextSibling) if (c.__k !== undefined) old.set(c.__k, c);
  const want = new Set();
  for (const v of vkids) { const c = old.get(v.k); if (c && fits(c, v)) want.add(c); }
  let cursor = parent.firstChild;
  for (const v of vkids) {
    while (cursor && !want.has(cursor)) { const next = cursor.nextSibling; retire(parent, cursor); cursor = next; }
    let node = old.get(v.k);
    if (node && want.has(node)) { want.delete(node); update(node, v, host, false); }
    else node = create(v, host);
    if (node === cursor) cursor = cursor.nextSibling;
    else parent.insertBefore(node, cursor);
  }
  while (cursor) { const next = cursor.nextSibling; retire(parent, cursor); cursor = next; }
}

/* mount(container, template, component, {onError}) puts the component in the container. */
export function mount(container, template, component, opts = {}) {
  const tpl = typeof template === 'string' ? compile(template, opts) : template;
  const host = { refs: new Set(), onError: opts.onError, frame: 0, timer: 0, dead: false };
  const render = () => {
    cancelAnimationFrame(host.frame); clearTimeout(host.timer); host.frame = host.timer = 0;
    if (host.dead) return;
    let vals;
    try { vals = component.renderVals(); } catch (err) { (opts.onError || console.error)(err, { in: 'renderVals' }); return; }
    patch(container, build(tpl.kids, vals, '', []), host);
    for (const n of host.refs) if (!n.isConnected) { setRef(n.__ref, null); n.__ref = null; host.refs.delete(n); }
  };
  component.__schedule = () => {
    if (holds > 0) { waiting.add(component.__schedule); return; }
    if (host.frame || host.dead) return;
    host.frame = requestAnimationFrame(render);
    host.timer = setTimeout(render, 100); // a hidden tab gets no frames
  };
  mounted.add(render);
  render();
  component.componentDidMount();
  return {
    component,
    render,
    flush: () => { if (host.frame) render(); },
    unmount: () => {
      host.dead = true; mounted.delete(render); cancelAnimationFrame(host.frame); clearTimeout(host.timer);
      container.textContent = '';
      for (const n of host.refs) setRef(n.__ref, null);
      host.refs.clear();
    }
  };
}

export class DCLogic {
  constructor(props) {
    this.props = props || {};
    this.state = {};
  }
  setState(update) {
    const patchObj = typeof update === 'function' ? update(this.state, this.props) : update;
    if (patchObj) this.state = Object.assign({}, this.state, patchObj);
    if (this.__schedule) this.__schedule();
  }
  forceUpdate() { if (this.__schedule) this.__schedule(); }
  componentDidMount() {}
  renderVals() { return {}; }
}
