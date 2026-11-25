#!/usr/bin/env node
/* 单位知识库自测：不调模型，直接验数值裁决与换算说明。
   用法：node tools/单位换算自测.js                                   */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const ROOT = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];

const NEEDED = [
  'nums', 'normText', 'getFieldAlias', 'fieldNameOf', 'valueForField',
  'getUnitTable', 'unitFactor', 'parseNumUnit', 'numWithUnit', 'valueWithUnitForField',
  'numericVerdict', 'dirNote'
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
vm.runInContext(NEEDED.map(pick).join('\n'), sandbox);

const cases = [
  // [招标原文, 投标响应, 期望方向, 期望理由片段(可选)]
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

let pass = 0, fail = 0;
for (const [a, b, want, hint] of cases) {
  const v = sandbox.numericVerdict(a, b);
  const got = v ? v.dir : null;
  const note = v ? sandbox.dirNote(v.dir, v.av, v.bv, v) : '';
  const okDir = got === want;
  const okHint = !hint || note.includes(hint);
  if (okDir && okHint) { pass++; console.log(`OK  ${a} | ${b} → ${got || '不裁决'}  ${note}`); }
  else { fail++; console.log(`FAIL ${a} | ${b} → 期望${want || '不裁决'} 实得${got || '不裁决'} hint="${hint}" note="${note}"`); }
}
console.log(`\n通过 ${pass} / ${pass + fail}`);
if (fail) process.exit(1);
