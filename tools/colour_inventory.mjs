#!/usr/bin/env node
// Every colour the light design uses, where and for what, and how it looks in dark.
//
//     node tools/colour_inventory.mjs            the inventory, then the checks
//     node tools/colour_inventory.mjs --checks   only the checks
//
// Reads web/templates (inline styles and SVG colour attributes), web/css and web/logic.
// For each distinct colour: its count and the roles it's used in (background, text, line
// via border or inset ring, shadow, gradient, SVG paint, a value handed to a style hole).
// Then the checks, against web/theme.js (the lens) and web/css/theme.css:
//   1. every colour found is in the lens's table (else it falls to the rule by role);
//   2. contrast in dark: every text colour against the dark surfaces it sits on, and every
//      text-on-background pair written in one style string (and the agents' ink on their
//      colour, and their accent on their tint); body text 4.5:1, large text 3:1;
//   3. css/theme.css's dark values are what the lens gives for that colour and role.
// Node's standard library only. Exits 1 when a check fails.
import fs from 'node:fs';
import path from 'node:path';
import url from 'node:url';

const ROOT = path.join(path.dirname(url.fileURLToPath(import.meta.url)), '..', 'web');
const T = await import(url.pathToFileURL(path.join(ROOT, 'theme.js')).href);
const onlyChecks = process.argv.includes('--checks');

const walk = (dir, ext) => fs.readdirSync(dir, { withFileTypes: true }).flatMap((d) => {
  const p = path.join(dir, d.name);
  return d.isDirectory() ? walk(p, ext) : (p.endsWith(ext) ? [p] : []);
});
const COLOUR = /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|\b(?:white|black)\b/g;
const norm = (t) => {
  t = t.toLowerCase().replace(/\s+/g, '');
  if (t === 'white') return '#ffffff';
  if (t === 'black') return '#000000';
  if (/^#[0-9a-f]{3}$/.test(t)) return '#' + t.slice(1).split('').map((c) => c + c).join('');
  const m = t.match(/^rgba?\((\d+),(\d+),(\d+)(?:,([\d.]+))?\)$/);
  if (m) return 'rgba(' + m[1] + ',' + m[2] + ',' + m[3] + ',' + (m[4] == null ? 1 : +m[4]) + ')';
  return t;
};
const hexOf = (n) => { const m = n.match(/^rgba\((\d+),(\d+),(\d+)/); return m ? '#' + [m[1], m[2], m[3]].map((x) => (+x).toString(16).padStart(2, '0')).join('') : n; };

const seen = new Map(); // colour -> { n, roles: Map(role -> n), files: Set }
const add = (tok, role, file) => {
  const c = norm(tok);
  if (!/^#|^rgba/.test(c)) return;
  const e = seen.get(c) || { n: 0, roles: new Map(), files: new Set() };
  e.n++; e.roles.set(role, (e.roles.get(role) || 0) + 1); e.files.add(path.relative(ROOT, file));
  seen.set(c, e);
};
const NAME = { fg: 'text', bg: 'background', line: 'line', shadow: 'shadow' };
function fromStyle(style, file, pairs) {
  let bg = null, fg = null;
  for (const d of T.declarations(style)) {
    const role = T.roleOf(d.prop);
    if (!role) continue;
    if (role === 'box-shadow') {
      for (const layer of d.value.split(/,(?![^(]*\))/)) {
        const inset = /\binset\b/.test(layer);
        const nums = layer.replace(COLOUR, ' ').match(/-?[\d.]+(px)?/g) || [];
        const ring = inset || (nums.length > 2 ? parseFloat(nums[2]) : 0) === 0;
        for (const t of layer.match(COLOUR) || []) add(t, ring ? (inset ? 'line (inset ring)' : 'line (ring)') : 'shadow', file);
      }
      continue;
    }
    const grad = /gradient\(/.test(d.value);
    const what = grad ? 'gradient' : (d.prop === 'fill' || d.prop === 'stroke' ? 'svg ' + d.prop : (role === 'line' ? 'line (' + d.prop + ')' : NAME[role]));
    for (const t of d.value.match(COLOUR) || []) add(t, what, file);
    const one = (d.value.match(COLOUR) || []);
    if ((d.prop === 'background' || d.prop === 'background-color') && one.length === 1 && !grad && !/\{\{/.test(d.value)) bg = one[0];
    if (d.prop === 'color' && one.length === 1 && !/\{\{/.test(d.value)) fg = one[0];
  }
  if (bg && fg && pairs) pairs.push({ style, bg, fg, file });
}

const pairs = [];
// Templates: style attributes and SVG colour attributes.
for (const f of walk(path.join(ROOT, 'templates'), '.html')) {
  const s = fs.readFileSync(f, 'utf8');
  for (const m of s.matchAll(/\sstyle="([^"]*)"/g)) fromStyle(m[1], f, pairs);
  for (const m of s.matchAll(/\s(fill|stroke|stop-color|color)="([^"{]*)"/g)) for (const t of m[2].match(COLOUR) || []) add(t, 'svg ' + m[1] + ' attribute', f);
}
// Stylesheets (theme.css holds the dark values; it is checked below instead).
for (const f of walk(path.join(ROOT, 'css'), '.css')) {
  if (f.endsWith('theme.css')) continue;
  const s = fs.readFileSync(f, 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
  for (const m of s.matchAll(/\{([^}]*)\}/g)) fromStyle(m[1], f, pairs);
}
// Logic: colours in string literals, with the key they're handed under (a style hole).
const KEYROLE = (k) => {
  if (/^(fg|fc|tc|vc|nc|mc|c|ink|accent|badgeC|dotC|color|apptMarkColor|muteFg|bellFg|delFg)$/.test(k)) return /^(color)$/.test(k) ? 'agent colour (hole)' : (k === 'dotC' ? 'dot (hole)' : 'text (hole)');
  if (/(bg|Bg|tint|fill|dot|swatch|^c$)/.test(k)) return 'background (hole)';
  if (/(ring|Ring|shadow|halo|border)/.test(k)) return 'line or shadow (hole)';
  return 'hole value';
};
for (const f of walk(path.join(ROOT, 'logic'), '.js')) {
  const s = fs.readFileSync(f, 'utf8');
  for (const m of s.matchAll(/(?:(\w+)\s*:\s*[^,'"{}]*?)?'([^'\n]*)'/g)) {
    const lit = m[2];
    if (!COLOUR.test(lit)) continue;
    COLOUR.lastIndex = 0;
    const role = /\b0 0 0 \d|inset|solid|dashed/.test(lit) ? 'line or shadow (hole)' : KEYROLE(m[1] || '');
    for (const t of lit.match(COLOUR) || []) add(t, role, f);
  }
}

// ------------------------------------------------------------ groups, for reading
const GROUPS = [
  ['page ground', ['#f8fafc']],
  ['card surface (white)', ['#ffffff', '#fbfbfc', '#f7f7f9']],
  ['raised surface', ['#f1f5f9', '#eef2f7', '#f5f5f7', '#f2f2f5', '#f6f5f8']],
  ['hairline', ['#e2e8f0', '#e6e6ea', '#e4e4ea', '#e8e8ec', '#ececf0', '#ebe9ef', '#d6d1df', '#cbd5e1']],
  ['primary text', ['#0f172a', '#111114', '#1d1b22', '#000000']],
  ['secondary text', ['#475569', '#55555c', '#3c3c43', '#4b4458']],
  ['muted text', ['#64748b', '#94a3b8', '#8a94a0']],
  ['Donna (purple)', ['#6d28d9', '#f5f3ff', 'rgba(109,40,217,0.18)', 'rgba(109,40,217,0.15)', '#7c3aed']],
  ['Pepper (orange)', ['#c2410c', '#fff3ec', '#fde3d3', '#f6b48f', 'rgba(194,65,12,0.18)']],
  ['Moneypenny (yellow)', ['#ca8a04', '#854d0e', '#fefce8', '#a16207', '#eab308', 'rgba(202,138,4,0.22)']],
  ['me / success green', ['#16a34a', '#15803d', '#22c55e', '#14532d', '#052e16', '#dcfce7', '#f0fdf4']],
  ['urgent red', ['#b42318', '#d9392b', '#dc2626', '#c0392b', '#991b1b', '#7f1d1d', '#fef2f2', '#fecaca']],
  ['waiting amber', ['#fef3c7', '#fef9c3', '#78350f', '#d97706', '#d9730d']],
  ['blue (running, links)', ['#2563eb', '#1d4ed8', '#2f7fd1', '#7a5aa8']],
  ['Mac window buttons', ['#ff5f57', '#febc2e', '#28c840']],
  ['shadows, veils, glass', []]
];
const grouped = new Set(GROUPS.flatMap((g) => g[1]));

if (!onlyChecks) {
  const line = (c) => {
    const e = seen.get(c); if (!e) return null;
    const dark = { bg: T.mapColour(c, 'bg'), fg: T.mapColour(c, 'fg'), line: T.mapColour(c, 'line') };
    const roles = [...e.roles].sort((a, b) => b[1] - a[1]).map(([r, n]) => r + ' ' + n).join(', ');
    return '  ' + c.padEnd(24) + String(e.n).padStart(4) + '  ' + roles + '\n' + ' '.repeat(32) + 'dark: bg ' + dark.bg + ' · text ' + dark.fg + ' · line ' + dark.line;
  };
  console.log('Colours in the light design: ' + seen.size + ' distinct, ' + [...seen.values()].reduce((a, e) => a + e.n, 0) + ' uses\n');
  for (const [name, cs] of GROUPS) {
    const rows = (cs.length ? cs : [...seen.keys()].filter((c) => !grouped.has(c) && c.startsWith('rgba') && !/^rgba\(\d+,\d+,\d+,1\)$/.test(c))).map(line).filter(Boolean);
    if (rows.length) console.log(name + '\n' + rows.join('\n') + '\n');
    if (!cs.length) for (const c of seen.keys()) if (c.startsWith('rgba')) grouped.add(c);
  }
  const rest = [...seen.keys()].filter((c) => !grouped.has(c)).sort();
  if (rest.length) console.log('kinds of time, swatches, charts and the rest\n' + rest.map(line).join('\n') + '\n');
}

// ------------------------------------------------------------ checks
let fails = 0;
const say = (ok, t) => { if (!ok) fails++; console.log((ok ? 'ok    ' : 'FAIL  ') + t); };

// 1. In the table.
const tableKeys = new Set(Object.keys(T.TABLE));
const missing = [...seen.keys()].map(hexOf).filter((h) => /^#[0-9a-f]{6}$/.test(h) && !tableKeys.has(h));
const uniqMissing = [...new Set(missing)];
// The calendar's own colours (Google's palette) and the colour swatches are painted only as
// dots and swatches: the rule keeps them as they are, which is what they should be.
const KEEP = new Set(['#7986cb', '#33b679', '#8e24aa', '#e67c73', '#f6bf26', '#f4511e', '#039be5', '#616161', '#3f51b5', '#0b8043', '#d50000',
  '#ea580c', '#0d9488', '#9333ea', '#db2777']);
const unexplained = uniqMissing.filter((h) => !KEEP.has(h));
say(!unexplained.length, 'every colour is in the table' + (unexplained.length ? ': missing ' + unexplained.join(' ') : ' (' + uniqMissing.length + ' dot and swatch colours left to the rule, which keeps them)'));

// 2. Contrast in dark.
const D = (c, r) => T.mapColour(c, r);
const SURF = { 'card': D('#ffffff', 'bg'), 'page': D('#f8fafc', 'bg'), 'raised': D('#f1f5f9', 'bg') };
const TINTS = { donna: '#f5f3ff', pepper: '#fff3ec', mp: '#fefce8', red: '#fef2f2', amber: '#fef3c7', green: '#dcfce7', greenSoft: '#f0fdf4' };
const textColours = [...seen].filter(([c, e]) => [...e.roles.keys()].some((r) => /^text/.test(r))).map(([c]) => c);
const out = [];
for (const c of textColours) {
  if (/^rgba/.test(c) && !/,1\)$/.test(c)) continue;
  const h = hexOf(c), fg = D(h, 'fg');
  if (h === '#ffffff' || (seen.get(c).roles.get('text (hole)') && !seen.get(c).roles.get('text'))) {
    // white text and hole text: only on what they're written for (checked as pairs below)
  }
  for (const [n, s] of Object.entries(SURF)) {
    const r = T.contrast(fg, s);
    if (r < 4.5 && h !== '#ffffff' && !['#f8fafc', '#f1f5f9', '#e2e8f0', '#cbd5e1'].includes(h) && !/^#(f[0-9a-f]{5})$/.test(h)) out.push([h + ' → ' + fg + ' on ' + n + ' ' + s, r]);
  }
}
const surfaceFails = out.filter(([, r]) => r < 4.5);
say(!surfaceFails.length, 'text colours on the dark card, page and raised surfaces, 4.5:1' + (surfaceFails.length ? ':\n' + surfaceFails.map(([t, r]) => '        ' + t + '  ' + r.toFixed(2)).join('\n') : ''));

const pairFails = [];
let pairN = 0;
for (const p of pairs) {
  const lensed = T.lens(p.style);
  let bg = null, fg = null;
  for (const d of T.declarations(lensed)) {
    if ((d.prop === 'background' || d.prop === 'background-color') && !/gradient/.test(d.value)) bg = (d.value.match(COLOUR) || [])[0];
    if (d.prop === 'color') fg = (d.value.match(COLOUR) || [])[0];
  }
  if (!bg || !fg || /rgba/.test(bg) || /rgba/.test(fg)) continue;
  pairN++;
  const light = T.contrast(p.fg, p.bg), dark = T.contrast(fg, bg);
  const size = +(p.style.match(/font-size:\s*(\d+)/) || p.style.match(/font:\s*\d+\s+(\d+)px/) || [0, 15])[1];
  const need = size >= 24 ? 3 : 4.5;
  if (dark < need && dark < light - 0.01) pairFails.push(p.fg + ' on ' + p.bg + ' → ' + fg + ' on ' + bg + '  ' + dark.toFixed(2) + ' (light ' + light.toFixed(2) + ')  ' + path.relative(ROOT, p.file));
}
say(!pairFails.length, pairN + ' text-on-background pairs written in one style string, in dark at least 4.5:1 (3:1 large) or no worse than light' + (pairFails.length ? ':\n        ' + [...new Set(pairFails)].join('\n        ') : ''));

const AGENTS = [['Donna', '#6d28d9', '#ffffff', '#f5f3ff', '#6d28d9'], ['Pepper', '#c2410c', '#ffffff', '#fff3ec', '#c2410c'], ['Moneypenny', '#ca8a04', '#0f172a', '#fefce8', '#854d0e']];
for (const [n, color, ink, tint, accent] of AGENTS) {
  const st = T.lens('background: ' + color + '; color: ' + ink);
  const [b, f] = st.match(COLOUR);
  const r1 = T.contrast(f, b), r2 = T.contrast(D(accent, 'fg'), D(tint, 'bg')), r3 = T.contrast(D(accent, 'fg'), SURF.card);
  say(r1 >= 4.5 && r2 >= 4.5 && r3 >= 4.5, n + ': ink on her colour ' + r1.toFixed(2) + ', her accent on her tint ' + r2.toFixed(2) + ', on a card ' + r3.toFixed(2));
}
// The tints are still told apart from the card.
for (const [n, t] of Object.entries(TINTS)) {
  const d = D(t, 'bg'), r = T.contrast(d, SURF.card);
  say(d !== SURF.card, n + ' tint ' + t + ' → ' + d + ' (against the card ' + r.toFixed(2) + ':1, a different surface)');
}
// Lines can be seen on the card and the page.
for (const l of ['#e2e8f0', '#cbd5e1', '#f1f5f9']) {
  const d = D(l, 'line');
  say(T.contrast(d, SURF.card) >= 1.15, 'line ' + l + ' → ' + d + ': ' + T.contrast(d, SURF.card).toFixed(2) + ':1 on the card, ' + T.contrast(d, SURF.page).toFixed(2) + ':1 on the page');
}

// 3. theme.css agrees with the lens.
const css = fs.readFileSync(path.join(ROOT, 'css', 'theme.css'), 'utf8').replace(/\/\*[\s\S]*?\*\//g, '');
const block = (sel) => Object.fromEntries([...(css.split(sel)[1] || '').split('}')[0].matchAll(/(--hq-[\w-]+):\s*([^;]+);/g)].map((m) => [m[1], m[2].trim()]));
const L = block(':root {'), K = block('[data-theme="dark"] {');
const ROLE = { '--hq-ground': 'bg', '--hq-card': 'bg', '--hq-raised': 'bg', '--hq-hair': 'line', '--hq-hair-soft': 'line', '--hq-ink': 'fg', '--hq-ink-2': 'fg', '--hq-placeholder': 'fg', '--hq-float': 'shadow' };
const bad = Object.keys(ROLE).filter((v) => norm(T.mapColour(L[v], ROLE[v])) !== norm(K[v] || ''));
say(!bad.length, 'css/theme.css dark values match the lens' + (bad.length ? ': ' + bad.map((v) => v + ' is ' + K[v] + ', lens ' + T.mapColour(L[v], ROLE[v])).join('; ') : ' (' + Object.keys(ROLE).length + ' variables)'));

console.log(fails ? fails + ' check(s) failed' : 'all checks pass');
process.exit(fails ? 1 : 0);
