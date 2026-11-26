// theme.js: light and dark.
//
// The design is drawn in light only: its colours are written inline in the templates and
// handed in by the logic modules. Dark is a colour lens over that: one table maps every
// colour the light design uses to its dark counterpart, per role (a surface, text, a line,
// a shadow, a veil), and every inline style passes through lens() on its way into the DOM.
// The stylesheets use the same values as CSS variables (css/theme.css).
//
// lens(style) reads a style string as declarations and maps each colour in it by what the
// property does with it: `color: #ffffff` is text, `background: #ffffff` a surface, a
// `box-shadow: 0 0 0 1px #e2e8f0 inset` a line, a blurred box-shadow a shadow, a see-through
// background a veil. Everything else in the string stays as written, so selectors that
// match inline styles by their text keep matching. Colours the table doesn't know (an
// agent's own colour from the server, the tints the core mixes from it) get a rule by role.
// When one style string sets both a background and a text colour, the text is checked
// against the background and swapped for a readable one if the mapping made it unreadable.
//
// apply(mode) with 'light', 'dark' or 'system' sets data-theme on <html>, installs or clears
// the engine's lens, sets the page background and theme-color, and renders everything
// again. 'system' follows the device, also when it changes while the page is open.
// The choice is kept on the device as `hq-theme` ('light', 'dark', or nothing for system).

// ---------------------------------------------------------------- the table
// light colour -> dark colour. A string is the same for every role; an object gives it per
// role: bg (backgrounds and painted shapes), fg (text and icons), line (borders, outlines
// and rings), shadow (soft shadows: { c, a } multiplies the alpha), veil (a see-through
// background, also { c, a }; with `from`, only from that alpha up). A role it doesn't name falls back to `all`, then to the rule.
// The groups below name what each colour is for in the design.
// TABLE-START
export const TABLE = {
  "#f8fafc": { "all": "#0b1017", "fg": "#0b1017" },
  "#ffffff": { "bg": "#131a24", "line": "#131a24", "fg": "#ffffff", "veil": { "c": "#131a24", "a": 1, "from": 0.5 } },
  "#f1f5f9": { "bg": "#1c2431", "line": "#1f2835", "fg": "#1c2431" },
  "#eef2f7": "#19212d",
  "#e2e8f0": { "all": "#273142", "fg": "#a7b2c2" },
  "#cbd5e1": { "all": "#3a475a", "fg": "#8794a8" },
  "#0f172a": { "all": "#e7ecf3", "shadow": { "c": "#000000", "a": 2.2 }, "veil": { "c": "#000000", "a": 1.6 } },
  "#475569": { "fg": "#a7b2c2", "line": "#5b6b80", "bg": "#2a3546" },
  "#64748b": { "fg": "#93a0b4", "all": "#64748b" },
  "#94a3b8": { "fg": "#8794a8", "bg": "#4a576b", "line": "#4a576b" },
  "#111114": { "all": "#e7ecf3", "shadow": { "c": "#000000", "a": 2.2 }, "veil": { "c": "#000000", "a": 1.6 } },
  "#1d1b22": { "all": "#e4e2ea", "shadow": { "c": "#000000", "a": 3 } },
  "#55555c": { "fg": "#a9b0bc", "all": "#4a4f59" },
  "#3c3c43": { "fg": "#c3c9d3", "all": "#4a4f59" },
  "#4b4458": { "fg": "#b4accc", "all": "#4b4458" },
  "#f5f5f7": "#161c25",
  "#f7f7f9": "#151b24",
  "#fbfbfc": "#141a23",
  "#f2f2f5": "#1a212c",
  "#f6f5f8": "#1a1f2a",
  "#ececf0": "#222a36",
  "#e8e8ec": "#232b37",
  "#e6e6ea": "#262f3c",
  "#e4e4ea": "#28313f",
  "#ebe9ef": "#242a37",
  "#d6d1df": "#3b3a4c",
  "#8a94a0": { "fg": "#97a1ad", "all": "#8a94a0" },

  "#6d28d9": { "bg": "#6d28d9", "fg": "#b9a0ff", "line": "#8b5cf6", "shadow": { "c": "#8b5cf6", "a": 1 } },
  "#f5f3ff": { "all": "#1e1934", "fg": "#f5f3ff" },
  "#7c3aed": { "bg": "#7c3aed", "fg": "#b9a0ff" },
  "#c2410c": { "bg": "#c2410c", "fg": "#ff9561", "line": "#ea6a2e", "shadow": { "c": "#ea6a2e", "a": 1 } },
  "#fff3ec": { "all": "#291a13", "fg": "#fff3ec" },
  "#fde3d3": { "all": "#3a2318", "fg": "#fde3d3" },
  "#f6b48f": { "all": "#7a3d1e", "fg": "#f6b48f" },
  "#ca8a04": { "bg": "#ca8a04", "fg": "#e8b52c", "line": "#ca8a04", "shadow": { "c": "#ca8a04", "a": 1 } },
  "#854d0e": { "fg": "#ecbd45", "all": "#854d0e" },
  "#fefce8": { "all": "#25200f", "fg": "#fefce8" },
  "#a16207": { "fg": "#e0b23a", "line": "#c99a1f", "bg": "#a16207" },
  "#eab308": "#eab308",

  "#16a34a": { "bg": "#16a34a", "fg": "#55d487", "line": "#22a95a" },
  "#15803d": { "fg": "#55d487", "bg": "#15803d", "line": "#22a95a" },
  "#22c55e": "#22c55e",
  "#14532d": { "fg": "#a6efc1", "all": "#14532d" },
  "#052e16": { "fg": "#bdf5d0", "all": "#052e16" },
  "#dcfce7": { "all": "#12301f", "fg": "#dcfce7" },
  "#f0fdf4": { "all": "#0e2417", "fg": "#f0fdf4" },

  "#b42318": { "fg": "#ff8b7d", "bg": "#b42318", "line": "#e0503f" },
  "#d9392b": { "bg": "#d9392b", "fg": "#ff8b7d", "line": "#e0503f" },
  "#dc2626": { "all": "#e5484d", "fg": "#ff8b7d" },
  "#c0392b": { "all": "#d9473a", "fg": "#ff8b7d" },
  "#991b1b": { "fg": "#ffa59c", "all": "#991b1b" },
  "#7f1d1d": { "fg": "#ffc4bc", "all": "#7f1d1d" },
  "#fef2f2": { "all": "#2b1517", "fg": "#fef2f2" },
  "#fecaca": { "line": "#6e2b2d", "bg": "#4a1f22", "fg": "#fecaca" },

  "#fef3c7": { "all": "#2e2511", "fg": "#fef3c7" },
  "#fef9c3": { "all": "#2b2711", "fg": "#fef9c3" },
  "#78350f": { "fg": "#fcd57a", "all": "#78350f" },
  "#d97706": { "all": "#e08a12", "fg": "#f5b041" },
  "#d9730d": { "all": "#e08a1f", "fg": "#f5b041" },

  "#2563eb": { "all": "#3b7af5", "fg": "#86aefc" },
  "#1d4ed8": { "all": "#3366e8", "fg": "#93b6ff" },
  "#2f7fd1": { "all": "#3d8be0", "fg": "#8cbcf0" },
  "#7a5aa8": { "all": "#8a6ab8", "fg": "#c0a8e6" },

  "#ff5f57": "#ff5f57",
  "#febc2e": "#febc2e",
  "#28c840": "#28c840",
  "#000000": { "all": "#000000", "fg": "#e7ecf3" }
};
// TABLE-END

// The page itself, for the moments before the design draws (and for theme-color).
export const PAGE = { light: '#f8fafc', dark: '#0b1017' };
// The surface text is read against when the rule has to pick a lightness (the card).
const CARD = '#131a24';

// ---------------------------------------------------------------- colours
const NAMED = { white: '#ffffff', black: '#000000' };
const COLOUR = /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|\b(?:white|black)\b/g;

function parse(tok) {
  const t = tok.toLowerCase();
  if (NAMED[t]) return parse(NAMED[t]);
  if (t[0] === '#') {
    let h = t.slice(1);
    if (h.length === 3 || h.length === 4) h = h.split('').map((c) => c + c).join('');
    if (h.length !== 6 && h.length !== 8) return null;
    const n = (i) => parseInt(h.slice(i, i + 2), 16);
    return { r: n(0), g: n(2), b: n(4), a: h.length === 8 ? n(6) / 255 : 1 };
  }
  const m = t.match(/rgba?\(\s*([\d.]+)\s*[, ]\s*([\d.]+)\s*[, ]\s*([\d.]+)\s*(?:[,/]\s*([\d.]+%?))?\s*\)/);
  if (!m) return null;
  let a = m[4] == null ? 1 : (m[4].endsWith('%') ? parseFloat(m[4]) / 100 : parseFloat(m[4]));
  return { r: +m[1], g: +m[2], b: +m[3], a };
}
const hex2 = (n) => Math.max(0, Math.min(255, Math.round(n))).toString(16).padStart(2, '0');
const toHex = (c) => '#' + hex2(c.r) + hex2(c.g) + hex2(c.b);
const round = (a) => Math.round(Math.max(0, Math.min(1, a)) * 1000) / 1000;
function write(c, a) {
  if (a >= 1) return toHex(c);
  return 'rgba(' + Math.round(c.r) + ',' + Math.round(c.g) + ',' + Math.round(c.b) + ',' + round(a) + ')';
}

export function luminance(c) {
  const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
}
export function contrast(a, b) {
  const x = typeof a === 'string' ? parse(a) : a, y = typeof b === 'string' ? parse(b) : b;
  const l1 = luminance(x), l2 = luminance(y);
  return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
}
function hsl(c) {
  const r = c.r / 255, g = c.g / 255, b = c.b / 255;
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx === mn) return { h: 0, s: 0, l };
  const d = mx - mn, s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
  const h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return { h: h / 6, s, l };
}
function rgb(h, s, l) {
  const k = (n) => (n + h * 12) % 12, a = s * Math.min(l, 1 - l);
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, 9 - k(n), 1));
  return { r: f(0) * 255, g: f(8) * 255, b: f(4) * 255 };
}

// The rule for a colour the table doesn't know, by role.
function rule(c, role) {
  const { h, s, l } = hsl(c);
  if (role === 'shadow') return l < 0.35 ? { c: { r: 0, g: 0, b: 0 }, a: 2.2 } : { c, a: 1 };
  if (role === 'veil') return l < 0.35 ? { c: { r: 0, g: 0, b: 0 }, a: 1.6 } : { c, a: 1 };
  if (role === 'fg') {
    if (l < 0.25 && s < 0.35) return { c: parse('#e7ecf3'), a: 1 }; // dark ink
    let out = c, L = l;
    const card = parse(CARD);
    while (contrast(out, card) < 4.6 && L < 0.92) { L += 0.03; out = rgb(h, Math.min(s, 0.85), L); }
    return { c: out, a: 1 };
  }
  // bg and line
  if (l >= 0.85) return { c: rgb(h, Math.min(s, 1) * 0.4, role === 'line' ? 0.24 : 0.14), a: 1 }; // a light tint: deep, quiet
  if (l < 0.2 && s < 0.35) return { c: parse('#e7ecf3'), a: 1 }; // ink as a fill: inverted
  return { c, a: 1 };
}

function entry(key, role) {
  const e = TABLE[key];
  if (e == null) return null;
  if (typeof e === 'string') return e;
  if (e[role] != null) return e[role];
  if (role === 'veil' || role === 'shadow') return e.all != null ? e.all : (e.bg != null ? e.bg : null);
  return e.all != null ? e.all : null;
}

// One colour for one role: the same alpha (times the table's or the rule's factor).
const one = new Map();
export function mapColour(tok, role) {
  const k = role + '|' + tok;
  let out = one.get(k);
  if (out !== undefined) return out;
  const c = parse(tok);
  if (!c) out = tok;
  else {
    let r = role;
    if (role === 'bg' && c.a < 1) r = 'veil';
    const e = entry(toHex(c), r);
    let to, fac = 1;
    if (e == null) { const x = rule(c, r); to = x.c; fac = x.a; }
    else if (typeof e === 'object' && e.from != null && c.a < e.from) to = c; // a faint veil (glass on a colour) stays
    else if (typeof e === 'object') { to = parse(e.c); fac = e.a == null ? 1 : e.a; }
    else to = parse(e);
    // A see-through veil of a light colour stays as it is (white glass on an agent's colour).
    if (r === 'veil' && e == null && hsl(c).l >= 0.35) to = c;
    out = (c.a >= 1 && fac === 1) ? toHex(to) : write(to, c.a * fac);
  }
  one.set(k, out);
  return out;
}

// ---------------------------------------------------------------- style strings
const ROLE_OF = (p) => {
  if (p === 'color' || p === 'caret-color' || p === '-webkit-text-fill-color' || p === 'text-decoration-color') return 'fg';
  if (p === 'box-shadow') return 'box-shadow';
  if (p === 'text-shadow') return 'shadow';
  if (p.startsWith('background') || p === 'fill' || p === 'stroke' || p === 'accent-color' || p === 'stop-color' || p === 'flood-color') return 'bg';
  if (p.startsWith('border') || p.startsWith('outline') || p === 'column-rule' || p === 'column-rule-color') return 'line';
  if (p === 'filter' || p === 'backdrop-filter') return 'shadow';
  return null;
};

// Split at a character, outside brackets and quotes.
function splitTop(s, ch) {
  const out = []; let depth = 0, q = '', last = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (q) { if (c === q) q = ''; continue; }
    if (c === '"' || c === "'") q = c;
    else if (c === '(') depth++;
    else if (c === ')') depth--;
    else if (c === ch && depth === 0) { out.push(s.slice(last, i)); last = i + 1; }
  }
  out.push(s.slice(last));
  return out;
}

const recolour = (v, role) => v.replace(COLOUR, (t) => mapColour(t, role));

// A box-shadow: per layer, a ring (inset, or no blur) is a line, the rest a shadow.
function shadowValue(v) {
  return splitTop(v, ',').map((layer) => {
    const inset = /\binset\b/.test(layer);
    const lens = layer.replace(COLOUR, ' ').match(/-?[\d.]+(px|rem|em)?/g) || [];
    const blur = lens.length > 2 ? parseFloat(lens[2]) : 0;
    return recolour(layer, inset || blur === 0 ? 'line' : 'shadow');
  }).join(',');
}

// The declarations of a style string: [{ prop, start, end }] with the value's place.
export function declarations(style) {
  const out = []; let at = 0;
  for (const part of splitTop(style, ';')) {
    const i = part.indexOf(':');
    if (i > 0) out.push({ prop: part.slice(0, i).trim().toLowerCase(), start: at + i + 1, end: at + part.length, value: part.slice(i + 1) });
    at += part.length + 1;
  }
  return out;
}

export function roleOf(prop) { return ROLE_OF(prop); }

const memo = new Map();
export function lens(style) {
  if (typeof style !== 'string' || !style) return style;
  let out = memo.get(style);
  if (out !== undefined) return out;
  COLOUR.lastIndex = 0;
  if (!COLOUR.test(style)) { memo.set(style, style); return style; }
  COLOUR.lastIndex = 0;
  const ds = declarations(style);
  let s = '', at = 0, bg = null, fg = null, fgAt = -1;
  const pieces = [];
  for (const d of ds) {
    const role = ROLE_OF(d.prop);
    if (!role) continue;
    const nv = role === 'box-shadow' ? shadowValue(d.value) : recolour(d.value, role);
    pieces.push({ d, nv });
    if ((d.prop === 'background' || d.prop === 'background-color') && !/gradient|url\(/.test(d.value)) bg = { from: d.value, to: nv };
    if (d.prop === 'color') { fg = { from: d.value, to: nv }; fgAt = pieces.length - 1; }
  }
  // Text and background set together: the text stays readable on the mapped background.
  if (bg && fg) {
    const b = solid(bg.to), f0 = solid(fg.to);
    if (b && f0 && contrast(f0, b) < 4.5) {
      const was = solid(fg.from), wasBg = solid(bg.from);
      const light = was && wasBg ? contrast(was, wasBg) : 0;
      // Only where the mapping made it worse: a pair the design drew low stays as drawn.
      if (light >= 3 && contrast(f0, b) < light - 0.01) {
        const cands = [fg.from.trim(), '#ffffff', PAGE.dark, '#e7ecf3'].map(solid).filter(Boolean);
        const pick = cands.find((x) => contrast(x, b) >= 4.5) || cands.sort((x, y) => contrast(y, b) - contrast(x, b))[0];
        if (pick && contrast(pick, b) > contrast(f0, b)) pieces[fgAt].nv = fg.to.replace(COLOUR, toHex(pick));
      }
    }
  }
  for (const { d, nv } of pieces) { s += style.slice(at, d.start) + nv; at = d.end; }
  out = s + style.slice(at);
  if (memo.size > 8000) memo.clear();
  memo.set(style, out);
  return out;
}
function solid(v) {
  if (!v) return null;
  const m = String(v).match(COLOUR);
  if (!m || m.length !== 1) return null;
  const c = parse(m[0]);
  return c && c.a >= 0.99 ? c : null;
}

// ---------------------------------------------------------------- applying it
let hooks = null, chosen = 'system', mq = null;
const KEY = 'hq-theme';
const readStored = () => { try { const v = localStorage.getItem(KEY); return v === 'light' || v === 'dark' ? v : 'system'; } catch (e) { return 'system'; } };
const urlTheme = () => { try { const v = new URLSearchParams(location.search).get('theme'); return v === 'light' || v === 'dark' ? v : null; } catch (e) { return null; } };

// The theme in use now: 'light' or 'dark'.
export function current() {
  const p = urlTheme() || chosen;
  if (p === 'light' || p === 'dark') return p;
  return mq && mq.matches ? 'dark' : 'light';
}
// What is picked: 'system', 'light' or 'dark' (?theme= for testing wins over it, unstored).
export function picked() { return chosen; }

function paint() {
  if (typeof document === 'undefined') return;
  const t = current(), root = document.documentElement;
  if (root.dataset.theme !== t) root.dataset.theme = t;
  root.style.colorScheme = t === 'dark' ? 'dark' : '';
  root.style.background = PAGE[t];
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.setAttribute('content', PAGE[t]);
  if (hooks) {
    const want = t === 'dark' ? lens : null;
    if (hooks.lens !== want) { hooks.lens = want; hooks.setStyleLens(want); hooks.rerenderAll(); }
  }
}

// init({ setStyleLens, rerenderAll }) from boot, before the first render.
export function init(engine) {
  chosen = readStored();
  hooks = { setStyleLens: engine.setStyleLens, rerenderAll: engine.rerenderAll, lens: undefined };
  if (typeof window !== 'undefined' && window.matchMedia && !mq) {
    mq = window.matchMedia('(prefers-color-scheme: dark)');
    const on = () => { if (chosen === 'system') paint(); };
    if (mq.addEventListener) mq.addEventListener('change', on); else if (mq.addListener) mq.addListener(on);
    window.addEventListener('storage', (e) => { if (e.key === KEY) { chosen = readStored(); paint(); } });
  }
  paint();
}

// apply(mode): 'light' | 'dark' | 'system'. Kept on the device as hq-theme.
export function apply(mode, { store = true } = {}) {
  chosen = mode === 'light' || mode === 'dark' ? mode : 'system';
  if (store) { try { if (chosen === 'system') localStorage.removeItem(KEY); else localStorage.setItem(KEY, chosen); } catch (e) { /* private mode */ } }
  paint();
  return current();
}

// ---------------------------------------------------------------- a look at the page
// audit(root): every piece of visible text under root whose colour, against the background
// it really sits on, is under 4.5:1 (3:1 for large text). For checking by hand in a browser.
export function audit(root = document.getElementById('app')) {
  const bad = [];
  const opaque = (el) => {
    const layers = [];
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n), c = parse(cs.backgroundColor);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') return { c: null, el: n };
      if (c && c.a > 0) { layers.push(c); if (c.a >= 0.99) break; }
    }
    let base = parse(PAGE[current()]);
    for (let i = layers.length - 1; i >= 0; i--) { const l = layers[i]; base = { r: l.r * l.a + base.r * (1 - l.a), g: l.g * l.a + base.g * (1 - l.a), b: l.b * l.a + base.b * (1 - l.a), a: 1 }; }
    return { c: base };
  };
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  const seen = new Set();
  for (let t = walker.nextNode(); t; t = walker.nextNode()) {
    const el = t.parentElement;
    if (!el || seen.has(el) || !t.data.trim()) continue;
    seen.add(el);
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || +cs.opacity === 0) continue;
    const f = parse(cs.color);
    const b = opaque(el);
    if (!f || !b.c) continue;
    let op = 1; for (let n = el; n && n.nodeType === 1; n = n.parentElement) op *= +getComputedStyle(n).opacity;
    const fa = f.a * op;
    const fc = { r: f.r * fa + b.c.r * (1 - fa), g: f.g * fa + b.c.g * (1 - fa), b: f.b * fa + b.c.b * (1 - fa) };
    const size = parseFloat(cs.fontSize), large = size >= 24 || (size >= 18.66 && +cs.fontWeight >= 700);
    const ratio = contrast(fc, b.c);
    if (ratio < (large ? 3 : 4.5)) bad.push({ text: t.data.trim().slice(0, 40), ratio: Math.round(ratio * 100) / 100, color: cs.color, on: toHex(b.c), size, el });
  }
  return bad;
}
