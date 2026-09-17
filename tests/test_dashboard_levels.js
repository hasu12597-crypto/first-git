// Run from the repository root: node tests/test_dashboard_levels.js
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
const vm = require('node:vm');
const html = process.argv[2] ? require('node:fs').readFileSync(process.argv[2], 'utf8') : execFileSync(process.env.PYTHON || 'python', ['-c',
  'import metrics; print(metrics.build_dashboard_html({"lead_time_hours": 33.3/3600}))'
], {encoding: 'utf8', env: {...process.env, PYTHONIOENCODING: 'utf-8', PYTHONDONTWRITEBYTECODE: '1'}});
assert.equal((html.match(/class="card"/g) || []).length, 4);
const elements = new Map();
const rows = ['elite','unclassified','high','medium','low'].map(level => ({
  dataset: {level}, active: false, attributes: {},
  classList: {toggle(_name, value) { rows.find(r => r.dataset.level === level).active = value; }},
  setAttribute(k,v) {this.attributes[k] = v;}, removeAttribute(k) {delete this.attributes[k];}
}));
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1].replace(/\n\s*loadMetrics\(\);\s*$/, '');
const context = vm.createContext({window: {}, document: {
  getElementById(id) { if (!elements.has(id)) elements.set(id, {}); return elements.get(id); },
  querySelectorAll() { return rows; }
}});
vm.runInContext(script, context);
const cases = [
 [0,'elite'], [33.3/3600,'elite'], [1-1e-10,'elite'], [1,'unclassified'],
 [24-1e-10,'unclassified'], [24,'high'], [168-1e-10,'high'],
 [168,'medium'], [720-1e-10,'medium'], [720,'low'], [1000,'low'],
 [null,'unavailable'], [undefined,'unavailable'], [-1,'unavailable'],
 [NaN,'unavailable'], [Infinity,'unavailable'], ['0.1','unavailable'], [true,'unavailable']
];
for (const [value,expected] of cases) {
  assert.equal(context.classifyLeadTime(value), expected, String(value));
  context.renderData({lead_time_hours:value, collection_errors:[]});
  assert.equal(rows.filter(r=>r.active).length, expected==='unavailable'?0:1);
  if(expected!=='unavailable') assert.equal(rows.find(r=>r.active).dataset.level, expected);
}
context.renderData({lead_time_hours:33.3/3600,collection_errors:[]});
assert.equal(elements.get('lead-time-level').textContent,'Elite');
context.renderData({lead_time_hours:33.3/3600,collection_errors:[{source:'test',type:'http_error',status:403}]});
assert.equal(elements.get('lead-time-level').textContent,'평가 불가');
assert.equal(rows.some(r=>r.active),false);
assert.equal(rows.some(r=>r.attributes['aria-current']),false);
// Exercise actual file:// fallback: fetch failure must still render embedded data.
context.fetch = async () => {throw new Error('local file fetch blocked');};
(async () => {
  await context.loadMetrics();
  assert.equal(elements.get('lead-time-level').textContent,'Elite');
  assert.equal(rows.find(r=>r.active).dataset.level,'elite');
  console.log('PASS: 18 value cases, 4 cards, stale highlight reset, API errors, embedded-data fallback');
})().catch(error=>{console.error(error);process.exitCode=1;});
