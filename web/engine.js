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
    if (n.type === 'text') out.push({ k: n.id + sfx, text: join(n.parts, scope) });
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
      for (const a of n.attrs) v.attrs[a.n] = a.get(scope);
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
    if (host.frame || host.dead) return;
    host.frame = requestAnimationFrame(render);
    host.timer = setTimeout(render, 100); // a hidden tab gets no frames
  };
  render();
  component.componentDidMount();
  return {
    component,
    render,
    flush: () => { if (host.frame) render(); },
    unmount: () => {
      host.dead = true; cancelAnimationFrame(host.frame); clearTimeout(host.timer);
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
