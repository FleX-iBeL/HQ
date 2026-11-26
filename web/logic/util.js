// Small helpers the areas share for the prototypes' house style. Shared and read-only for
// the wirers: add a helper here only if two areas need it.

// A chip: dark (or onBg) when on, white with a hairline when off.
export const chip = (on, onBg = '#0f172a') => ({ bg: on ? onBg : '#ffffff', fg: on ? '#ffffff' : '#475569', shadow: on ? 'none' : '0 0 0 1px #e2e8f0 inset' });

// A handler that flips state[key][id].
export const flip = (app, key, id) => () => app.setState((x) => ({ [key]: Object.assign({}, x[key], { [id]: !x[key][id] }) }));

// A tick circle: green and struck through when on.
export const tick = (on) => ({ ring: on ? '#16a34a' : '#cbd5e1', fill: on ? '#16a34a' : 'transparent', deco: on ? 'line-through' : 'none', fc: on ? '#94a3b8' : '#0f172a' });
