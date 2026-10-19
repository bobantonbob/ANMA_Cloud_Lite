const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

// Run the real dashboard renderer against consecutive telemetry snapshots.
const source = fs.readFileSync('static/js/dashboard.js', 'utf8');
const nodes = new Map();
const node = id => {
  if (!nodes.has(id)) nodes.set(id, {
    textContent: '', dataset: {}, style: {},
    classList: {toggle() {}},
  });
  return nodes.get(id);
};
let motionPath = 'M107 205 H260', paused = true, restarts = 0, incoming;
const particle = {
  classList: {toggle(name, value) { paused = value; }},
  querySelector() { return {
    getAttribute() { return motionPath; },
    setAttribute(name, value) { motionPath = value; },
    beginElement() { restarts++; },
  }; },
};
const context = {
  window: {ANMA: {}, dispatchEvent(event) { incoming = event.detail; }},
  CustomEvent: class { constructor(name, options) { this.detail = options.detail; } },
  localStorage: {getItem() { return 'en'; }},
  document: {
    getElementById: node,
    querySelector(selector) { return selector === '.grid-particle' ? particle : null; },
    querySelectorAll() { return []; },
    body: {classList: {toggle() {}}},
  },
};
vm.createContext(context);
vm.runInContext(source.slice(0, source.indexOf('const definitions=')) + 'window.testRender=render;})();', context);
context.render = context.window.testRender;
const sample = {online: true, grid_available: true, pv_power: 0, load_power: 1500, battery_power: 0};
for (const [watts, label, path, stopped] of [
  [1500, '→ IMPORT', 'M107 205 H260', false],
  [-1500, '← EXPORT', 'M260 205 H107', false],
  [0, 'IDLE', 'M107 205 H260', true],
  [1500, '→ IMPORT', 'M107 205 H260', false],
]) {
  context.render({...sample, grid_power: watts});
  assert.equal(node('flowGridStatusText').textContent, label);
  assert.equal(node('gridStatus').textContent, label);
  assert.equal(motionPath, path);
  assert.equal(paused, stopped);
  assert.equal(incoming.grid, watts, 'Source ring must receive the original signed reading');
  assert.equal(node('flowGrid').textContent, watts === 0 ? '0' : '1.500');
}
const before = restarts;
context.render({...sample, grid_power: 1500});
assert.equal(restarts, before, 'Stable readings must not reset the animation');
context.render({...sample, grid_power: null});
assert.equal(node('flowGridStatusText').textContent, 'NO DATA');
assert.equal(paused, true);
context.render({...sample, grid_power: 1500, grid_available: false});
assert.equal(node('flowGridStatusText').textContent, 'GRID UNAVAILABLE');
assert.equal(paused, true);
console.log('Signed telemetry → labels, animation, source ring and missing/offline states: OK');
