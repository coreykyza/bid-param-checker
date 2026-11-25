#!/usr/bin/env node
/* ============================================================
   端到端回归验证：不经浏览器，直接跑「拆分→AI判定→本地裁决」全链路。
   输出 results.json 供 tools/生成结果Excel.py 出表。

   用法：
     node tools/回归验证.js [源文件.xlsx行JSON]
   前置：
     python3 tools/xlsx转json.py <xlsx> > /tmp/rows.json
   ============================================================ */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const rowsFile = process.argv[2] || '/tmp/rows.json';
const outFile = process.argv[3] || '/tmp/results.json';

/* ---------- 1. 载入判定逻辑（与 index.html 同一份代码） ---------- */
function extractFromHtml() {
  const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');
  const m = html.match(/<script>([\s\S]*?)<\/script>/);
  if (!m) throw new Error('未找到主脚本');
  return m[1];
}
const mainJs = extractFromHtml();
const hwSpecs = fs.readFileSync(path.join(ROOT, 'data/hw-specs.js'), 'utf8');
const hwMatcher = fs.readFileSync(path.join(ROOT, 'data/hw-matcher.js'), 'utf8');

// 只取需要的纯函数，避免执行 DOM 相关代码
const NEEDED = [
  'normText', 'splitItems', 'nums', 'numWithUnit', 'itemSame', 'scoreOverlap',
  'numericVerdict', 'dirNote', 'hasAnyCounterpart', 'buildItemStates',
  'itemSeqLabel', 'itemBody', 'detailLine', 'statLine', 'formatResult', 'isNeg'
];
function pickFunctions(src, names) {
  const out = [];
  for (const name of names) {
    const re = new RegExp('function ' + name + '\\(');
    const m = re.exec(src);
    if (!m) { console.warn('⚠ 未找到函数', name); continue; }
    let i = src.indexOf('{', m.index);
    let depth = 0, j = i;
    while (j < src.length) {
      if (src[j] === '{') depth++;
      else if (src[j] === '}') { depth--; if (depth === 0) { j++; break; } }
      j++;
    }
    out.push(src.slice(m.index, j));
  }
  return out;
}

const sandbox = { console, JSON, Math, Date, String, Number, Array, Object, RegExp, isNaN, parseFloat, parseInt };
vm.createContext(sandbox);
vm.runInContext(hwSpecs, sandbox);
vm.runInContext(hwMatcher, sandbox);
vm.runInContext('var localStorage={getItem:function(){return null},setItem:function(){}};', sandbox);
vm.runInContext(pickFunctions(mainJs, NEEDED).join('\n'), sandbox);
vm.runInContext('loadHwSpecs();', sandbox);

// 抽 SYSTEM_PROMPT
const promptM = mainJs.match(/const SYSTEM_PROMPT=`([\s\S]*?)`;/);
const SYSTEM_PROMPT = promptM ? promptM[1] : '';
if (!SYSTEM_PROMPT) throw new Error('未找到 SYSTEM_PROMPT');

/* ---------- 2. 读配置（与 server.py 同一套规则） ---------- */
function readEnv() {
  const txt = fs.readFileSync(path.join(ROOT, '.env'), 'utf8');
  const out = {};
  for (const line of txt.split('\n')) {
    const l = line.trim();
    if (!l || l.startsWith('#') || !l.includes('=')) continue;
    const i = l.indexOf('=');
    out[l.slice(0, i).trim()] = l.slice(i + 1).trim().replace(/^["']|["']$/g, '');
  }
  return out;
}
const ENV = readEnv();
const cfg = (...keys) => {
  for (const k of keys) { const v = process.env[k] || ENV[k]; if (v) return v.trim(); }
  return '';
};
const KEY = cfg('LLM_API_KEY', 'DEEPSEEK_API_KEY', 'ZHIPU_API_KEY');
const MODEL_NAME = cfg('LLM_MODEL', 'DEEPSEEK_MODEL', 'ZHIPU_MODEL') || 'glm-4-flash';
const THINKING = cfg('LLM_THINKING');
const BASE = cfg('LLM_BASE_URL');
const DEFAULT_URLS = {
  deepseek: 'https://api.deepseek.com/v1/chat/completions',
  zhipu: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
};
let API = BASE || (MODEL_NAME.startsWith('deepseek') ? DEFAULT_URLS.deepseek : DEFAULT_URLS.zhipu);
if (!API.replace(/\/$/, '').endsWith('/chat/completions')) API = API.replace(/\/$/, '') + '/chat/completions';
if (!KEY) throw new Error('.env 里没有 LLM_API_KEY / ZHIPU_API_KEY');
console.log(`模型：${MODEL_NAME} | thinking=${THINKING || '-'} | ${API}`);

/* ---------- 3. 调模型（与前端 aiGradeBatch 等价） ---------- */
async function grade(rows) {
  const payload = {
    rows: rows.map(r => {
      const all = sandbox.splitItems(r.a);
      // 关键：分片时只发本片条目（之前漏了这步，一直发全部，导致结果错位/丢条目）
      const use = (r.onlyItems && r.onlyItems.length)
        ? all.filter((_, i) => r.onlyItems.includes(i))
        : all;
      const aForThis = (r.onlyItems && r.onlyItems.length)
        ? use.map(it => `${it.seqRaw || ''}${it.text}`).join('\n')
        : r.a;
      return {
        row: r.row,
        招标条目: use.map((it, k) => ({ n: k + 1, seq: it.seqRaw, text: it.text })),
        招标要求: aForThis,
        投标响应: r.b,
        本片条目数: use.length,
        本行总条目数: all.length
      };
    })
  };
  const body = {
    model: MODEL_NAME,
    temperature: 0.1,
    max_tokens: parseInt(cfg('LLM_MAX_TOKENS') || '8192', 10),
    response_format: { type: 'json_object' },
    messages: [
      { role: 'system', content: SYSTEM_PROMPT },
      { role: 'user', content: JSON.stringify(payload) }
    ]
  };
  if (THINKING === 'enabled' || THINKING === 'disabled') body.thinking = { type: THINKING };
  const ctl = new AbortController();
  const tid = setTimeout(() => ctl.abort(), 120000);
  try {
    const resp = await fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + KEY },
      body: JSON.stringify(body),
      signal: ctl.signal
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status + ' ' + (await resp.text()).slice(0, 200));
    const data = await resp.json();
    const content = data.choices[0].message.content;
    const clean = content.replace(/```json/g, '').replace(/```/g, '').trim();
    return JSON.parse(clean).results || [];
  } finally { clearTimeout(tid); }
}

/* ---------- 4. 主流程：本地预判 + 并发 ---------- */
(async () => {
  const rows = JSON.parse(fs.readFileSync(rowsFile, 'utf8'));
  const CONC = parseInt(process.env.CONC || '4', 10);
  const SHARD = 8;
  console.log(`共 ${rows.length} 行待核验，并发 ${CONC}`);

  const t0 = Date.now();

  // 阶段一：本地预判
  const pre = rows.map(p => ({ p, items: sandbox.buildItemStates(p, { items: [] }) }));
  const localDecided = pre.reduce((s, r) => s + r.items.filter(i => i.status !== 'pending').length, 0);
  const totalItems = pre.reduce((s, r) => s + r.items.length, 0);
  console.log(`本地预判：${localDecided}/${totalItems} 条可直接判定（${Math.round(localDecided / totalItems * 100)}%）`);

  // 收集 pending 并按片切分
  const jobs = [];
  let pendingCount = 0;
  for (const { p, items } of pre) {
    const idxs = [];
    items.forEach((it, i) => { if (it.status === 'pending') idxs.push(i); });
    pendingCount += idxs.length;
    for (let s = 0; s < idxs.length; s += SHARD) {
      jobs.push({ ...p, onlyItems: idxs.slice(s, s + SHARD) });
    }
  }
  console.log(`需 AI：${pendingCount} 条 → ${jobs.length} 片`);

  // 阶段二：并发发送
  const gradedMap = new Map();
  let finished = 0;
  async function worker() {
    while (cursor < jobs.length) {
      const idx = cursor++;
      const job = jobs[idx];
      try {
        const arr = await grade([job]);
        for (const r of arr) {
          if (!r) continue;
          const rowNo = Number(r.row);
          if (!gradedMap.has(rowNo)) gradedMap.set(rowNo, { row: rowNo, items: [] });
          const list = Array.isArray(r.items) ? r.items : [];
          list.forEach((item, k) => {
            if (job.onlyItems && job.onlyItems.length) {
              const g = job.onlyItems[k];
              item.n = (g != null ? g : job.onlyItems[0] + k) + 1;
            }
            gradedMap.get(rowNo).items.push(item);
          });
        }
      } catch (e) { /* 单片失败不影响其他片 */ }
      finished++;
      process.stdout.write(`\r  AI 判定 ${finished}/${jobs.length} 片…`);
    }
  }
  let cursor = 0;
  await Promise.all(Array.from({ length: Math.min(CONC, jobs.length || 1) }, worker));
  if (jobs.length) process.stdout.write('\n');

  // 阶段三：装配
  const assembled = pre.map(({ p }) => {
    const g = gradedMap.get(p.row) || { items: [] };
    return { p, items: sandbox.buildItemStates(p, g) };
  });

  // 阶段四：补漏（模型偶发漏返回，单条重试）
  // 按行聚合补漏（单条缺上下文，模型易宽松判匹配）
  const missingByRow = new Map();
  assembled.forEach(({ p, items }) => {
    const idxs = [];
    items.forEach((it, idx) => { if (it.status === 'pending') idxs.push(idx); });
    if (idxs.length) missingByRow.set(p.row, { p, idxs });
  });
  const missing = [...missingByRow.values()];
  if (missing.length) {
    const mTotal = missing.reduce((s, m) => s + m.idxs.length, 0);
    console.log(`补漏：${mTotal} 条（${missing.length} 行）按行重试`);
    let mCursor = 0, mDone = 0;
    async function mWorker() {
      while (mCursor < missing.length) {
        const m = missing[mCursor++];
        try {
          const arr = await grade([{ ...m.p, onlyItems: m.idxs }]);
          for (const r of arr) {
            const rowNo = Number(r.row);
            if (!gradedMap.has(rowNo)) gradedMap.set(rowNo, { row: rowNo, items: [] });
            const list = Array.isArray(r.items) ? r.items : [];
            list.forEach((item, k) => {
              const g = m.idxs[k];
              item.n = (g != null ? g : m.idxs[0] + k) + 1;
              gradedMap.get(rowNo).items.push(item);
            });
          }
        } catch (e) { /* 保持 pending */ }
        mDone++;
        process.stdout.write(`\r  补漏 ${mDone}/${missing.length} 行…`);
      }
    }
    await Promise.all(Array.from({ length: Math.min(CONC, missing.length) }, mWorker));
    process.stdout.write('\n');
    assembled.forEach(a => {
      const g = gradedMap.get(a.p.row) || { items: [] };
      a.items = sandbox.buildItemStates(a.p, g);
    });
  }

  const results = [];
  for (const { p, items } of assembled) {
    items.forEach(it => {
      if (it.status === 'pending') {
        it.status = 'uncertain';
        it.note = it.note || 'AI 未返回判定，需人工复核';
        it.confidence = it.confidence == null ? 0.5 : it.confidence;
      }
    });
    const cnt = { matched: 0, positive: 0, negative: 0, uncertain: 0 };
    items.forEach(it => cnt[it.status]++);
    const overall = (cnt.negative === 0 && cnt.uncertain === 0) ? '全部满足' : '部分满足';
    const rec = {
      row: p.row, a: p.a, b: p.b, overall, cnt,
      total: cnt.matched + cnt.positive + cnt.negative + cnt.uncertain,
      items: items.map(it => ({
        seqRaw: it.seqRaw, text: it.text, status: it.status,
        note: it.note, confidence: it.confidence
      }))
    };
    rec.cText = sandbox.formatResult({ ...rec, items, cnt });
    results.push(rec);
  }

  console.log(`总耗时 ${((Date.now() - t0) / 1000).toFixed(1)}s`);

  results.sort((x, y) => x.row - y.row);
  fs.writeFileSync(outFile, JSON.stringify(results, null, 2), 'utf8');

  // 汇总
  const stat = {
    总行: results.length,
    全部满足: results.filter(r => r.overall === '全部满足').length,
    部分满足: results.filter(r => r.overall === '部分满足').length,
    条目总数: results.reduce((s, r) => s + r.total, 0),
    统计自洽: results.every(r => r.total === r.cnt.matched + r.cnt.positive + r.cnt.negative + r.cnt.uncertain)
  };
  console.log('\n=== 汇总 ===');
  console.log(JSON.stringify(stat, null, 2));
  console.log('结果写入 ' + outFile);
})();
