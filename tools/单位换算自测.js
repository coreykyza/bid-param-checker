#!/usr/bin/env node
/* 单位知识库自测：不调模型，既验数值裁决，也验端到端装配。
   用法：node tools/单位换算自测.js                                   */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];

const NEEDED = [
  'nums', 'normText', 'splitItems', 'itemSame', 'scoreOverlap',
  'isGroupHeading', 'isBareValue', 'getFieldAlias', 'fieldNameOf', 'valueForField',
  'getUnitTable', 'unitFactor', 'parseNumUnit', 'numWithUnit', 'valueWithUnitForField',
  'numericVerdict', 'dirNote', 'hasAnyCounterpart', 'buildItemStates'
];
function pick(name) {
  const m = new RegExp('function ' + name + '\\(').exec(js);
  if (!m) throw new Error('未找到函数 ' + name);
  let i = js.indexOf('{', m.index), depth = 0, j = i;
  for (; j < js.length; j++) {
    if (js[j] === '{') depth++;
    else if (js[j] === '}') { depth--; if (!depth) { j++; break; } }
  }
  return js.slice(m.index, j);
}
const sandbox = { console, JSON, Math, Date, String, Number, Array, Object, RegExp, isNaN, parseFloat, parseInt };
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'data/hw-specs.js'), 'utf8'), sandbox);
vm.runInContext(fs.readFileSync(path.join(ROOT, 'data/hw-matcher.js'), 'utf8'), sandbox);
vm.runInContext('var localStorage={getItem:function(){return null},setItem:function(){}};', sandbox);
vm.runInContext(NEEDED.map(pick).join('\n'), sandbox);
vm.runInContext('loadHwSpecs();', sandbox);

let pass = 0, fail = 0;
function check(label, ok, detail) {
  if (ok) { pass++; console.log('OK  ' + label + '  ' + detail); }
  else { fail++; console.log('FAIL ' + label + '  ' + detail); }
}

/* ---------- 1. 函数级：数值裁决与换算说明 ---------- */
const cases = [
  ['续航时间≥110min', '16小时', 'positive', '960min'],
  ['续航时间≥110min', '1小时', 'negative', '60min'],
  ['内存≥8GB', '8192MB', 'matched', ''],
  ['主频≥2.3GHz', '2300MHz', 'matched', ''],
  ['功耗≤35W', '0.05kW', 'negative', '50W'],
  ['重量≤2.5kg', '2500g', 'matched', ''],
  ['屏幕尺寸≥55英寸', '140cm', 'positive', '55.1181英寸'],
  ['网络≥100Mbps', '1000Mbps', 'positive', ''],
  ['显存≥6GB', '6144MB', 'matched', ''],
  ['电池容量≥5000mAh', '5Ah', 'matched', ''],
  ['分辨率≥1920×1080px', '1920×1080', null, ''],
  ['算力≥6.5TFLOPS', '8TFLOPS', null, ''],
  ['续航时间≥110min', '16GB', null, ''],
  ['存储≥1TB', '1000GB', 'negative', ''],
];
for (const [a, b, want, hint] of cases) {
  const v = sandbox.numericVerdict(a, b);
  const got = v ? v.dir : null;
  const note = v ? sandbox.dirNote(v.dir, v.av, v.bv, v) : '';
  check(`${a} | ${b}`, got === want && (!hint || note.includes(hint)), `${got || '不裁决'} ${note}`);
}

/* ---------- 2. 端到端：无序号条目也要配上对 ---------- */
const e2e = [
  ['续航时间≥110min', '16小时', 'positive', '960min'],
  ['续航时间≥110min', '续航16小时', 'positive', '960min'],
  ['续航时间≥110min', '1小时', 'negative', '60min'],
];
for (const [a, b, wantStatus, hint] of e2e) {
  const it = sandbox.buildItemStates({ row: 1, a, b }, { items: [] })[0];
  check(`E2E ${a} | ${b}`, it.status === wantStatus && it.note.includes(hint), `${it.status} ${it.note} bText=${it.bText}`);
}

console.log(`\n通过 ${pass} / ${pass + fail}`);
if (fail) process.exit(1);
