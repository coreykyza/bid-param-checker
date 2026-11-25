# 招投标参数对照工具 · Bid Param Checker

上传 Excel，AI 逐条比对招标要求（A 列）与投标响应（B 列），在 C 列输出结论、负偏离标红、导出结果。

招投标核验的痛点不是"看不懂"，而是条目多、措辞绕、正负偏离容易判反。本工具把「拆条 → 四态判定 → 本地裁决 → AI 复核 → 出表」整条链路自动化，并用确定性规则兜底模型的不稳定输出。

## 实测效果

| 指标 | 数值 |
|---|---|
| 真实招标数据 | 28 行 / 239 个条目 |
| 全量核验耗时 | 14.9s（本地免费模型） |
| 本地确定性判定 | 143 / 239 条（60%），不调用模型 |
| AI 核验范围 | 16 条有结论条目（约 7%） |
| 统计自洽 | 四态之和恒等于条目总数 |
| 单位自测 | 17 / 17（含端到端；时间/存储/频率/功率/长度/重量/电量/网速等自动换算） |

## 快速开始

```bash
cd bid-param-checker
cp .env.example .env        # 填入自己的 API Key
python3 server.py           # 或双击 启动工具.command（带看门狗）
```

浏览器打开 **http://localhost:8765**，`/health` 返回 `key_configured: true` 即就绪。

不想配 Key 也可以直接双击 `index.html`，会自动进入演示模式（界面与导出一致，结论走本地规则）。

### 模型配置（双轨）

本地开发用火山方舟免费额度，生产/线上用 DeepSeek 官方付费，两套都写在 `.env` 里，切换只改几行：

```env
# 本地：火山免费额度（自动路由，按池顺序调用）
LLM_API_KEY=ark-你的key
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=deepseek-v4-1-flash-economy-261017
LLM_MODEL_POOL=deepseek-v4-1-flash-economy-261017,deepseek-v4-flash-ga-260731,glm-5-3-flash-260828,doubao-seed-evolving
LLM_VERIFY_MODEL=doubao-seed-evolving
LLM_VERIFY_POOL=doubao-seed-evolving,deepseek-v4-pro-ga-260813,glm-5-3-flash-260828
LLM_THINKING=disabled

# 生产：DeepSeek 官方付费（单模型即可，不需要池）
# LLM_API_KEY=sk-你的key
# LLM_BASE_URL=https://api.deepseek.com/v1
# LLM_MODEL=deepseek-flash
# LLM_MODEL_POOL=
# LLM_VERIFY_MODEL=deepseek-v4-pro
# LLM_VERIFY_POOL=
```

- **自动路由（v2.9）**：模型池按优先级排列，某模型返回 429（额度耗尽 / 被暂停）就自动拉黑并切下一个，拉黑记录写 `model_deadlist.json`，服务重启后仍有效。全部拉黑时清空重试一轮，防止换 key 后永久卡死。初判池与核验池独立，核验仍用异构模型。
- `/health` 返回 `route`、`model_pool`、`verify_pool`、`dead_models`，可直接看当前路由状态。
- V4 系列默认开启思考，结构化判定必须 `LLM_THINKING=disabled`，否则 reasoning 会挤占 `max_tokens` 导致返回空。
- 核验模型与初判模型刻意不同（异构），避免同一个模型复核自己。

## 使用流程

1. 点「下载样例 Excel」拿到标准格式（可选）
2. 上传 `.xlsx` / `.xls`：A 列 = 招标要求，B 列 = 投标响应，从第 2 行起
3. 点「开始核验」，实时显示进度
4. 右侧表格查看结论；含负偏离或待确认的行在 C 列标红
5. 点「导出核验结果 Excel」，下载 `原文件名_核验结果.xlsx`

## 输出格式

全部满足：

```
全部满足｜共10项：匹配8/正偏离2
```

部分满足（只列负偏离与待确认）：

```
部分满足｜共10项：负偏离2/待确认3/匹配3/正偏离2

负偏离：
  1、【1、】内存≥4G->响应2G，低于要求的4
  2、【二、1】课时≥8课时->响应6课时，低于要求的8

待确认：
  1、摄像头像素300w->投标参数中未找到对应内容，置信度0.5
  2、【3、】显卡性能不低于GTX1660->经核验转待确认（原正偏离）：显存6GB等于要求6GB，并非优于，置信度0.5
```

序号严格同步招标原文：原文 `1、` 输出 `【1、】`，原文 `二、1` 输出 `【二、1】`，无序号不加【】。四数之和恒等于条目总数。

## 核心设计

**四态判定，满足项不丢弃。** 每个条目必须归入 `matched` / `positive` / `negative` / `uncertain` 之一。早期版本只让模型报偏离项、前端靠减法反推满足数，出现过"共10项却列28条正偏离"，现已废弃。

**数值按字段名定位，不取全文第一个数字。** B 列常是一整行配置：`CPU：Intel I7 8700，内存：16GB DDR4，硬盘：120G固态`。取第一个数字会把型号 i7 的 `7` 当成内存响应值，把两个满足项判成负偏离。现在从 A 条目提取字段名（内存/硬盘/主频/显存…），在 B 中定位同字段的数值。

**单位不一致自动换算（v2.8）。** 内置 15 类基础单位知识库（时间/存储/网速/频率/功率/电压/电流/电量/长度/重量/体积/百分比/数量/温度/面积），两侧换算到同一基准再比：`续航≥110min` vs `16小时` → `响应16小时=960min，优于要求的110min`。大小写敏感（b/B、m/M、g/G、t/T 区分比特/字节、米/兆、克/吉、吨/太）。库里没有的单位（如 TFLOPS）仍保持待确认，不瞎判。

**分组标题不是条目。** "硬件参数""软件参数""4、配置"这类是分组名，其下挂的才是参数；带二级项的一级项也不是可比对条目。这两类在拆条阶段就被过滤，不送给模型。

**型号参数库。** 把投标侧型号展开成参数再比，解决「招标 ≥6核12线程、投标 i5-14500」这类需硬件知识才能判的场景。内置 101 个型号，可在界面查看/增删改。型号对比只比核数/线程/睿频，不比基础频率；点名"性能不低于 X 型号"时功耗不参与。

**AI 核验专家（v2.5）。** 只复核 `negative` / `positive` 这类有结论的高风险条目，把初判理由一起交给异构模型判断，但标注"仅供参考、请独立核对"。只有核验者指出具体矛盾且置信度 ≥0.7 才降级为待确认，并在 C 列注明原因。纯盲核（不给理由）会让核验者脑补不存在的靶子，已实测踩坑并修正。

## 项目结构

```
bid-param-checker/
├── index.html              # 单文件工具（UI + 拆条 + 判定 + 渲染 + 导出）
├── server.py               # 零依赖本地代理，隐藏 API Key
├── data/
│   ├── hw-specs.js         # 型号参数库（101 个型号）
│   └── hw-matcher.js       # 型号提取 / 规格比较 / 裁决
├── vendor/                 # xlsx-js-style
├── tools/
│   ├── 回归验证.js         # node 直调 API 跑全链路（不经浏览器）
│   ├── 单位换算自测.js     # 不调模型的单位裁决断言（秒级）
│   ├── xlsx转json.py       # 源表 → JSON
│   ├── 生成结果Excel.py    # JSON → 带标红的 xlsx
│   └── 验收检查.py         # 5 条验收自动核对
├── docs/                   # 需求基线 / 测试用例 / 案例复盘
├── .env.example            # 配置模板（无真实 Key）
├── CHANGELOG.md
└── README.md
```

命令行回归：

```bash
node tools/单位换算自测.js          # 秒级，不耗 token
python3 tools/xlsx转json.py 源文件.xlsx /tmp/rows.json
node tools/回归验证.js /tmp/rows.json /tmp/results.json
python3 tools/生成结果Excel.py 源文件.xlsx /tmp/results.json output/result.xlsx
python3 tools/验收检查.py output/result.xlsx
```

## 安全说明

API Key 只存在于本机 `.env`，`.gitignore` 已排除 `.env` / `.env.*` / `*.bak` / `*.pack` 等，不进前端源码、不进仓库。前端只与 `localhost:8765` 通信。历史上曾因误把 key 打进仓库而重建过三次，请保持 `.env.example` 只有占位符。

## 文档

- `docs/01-需求基线.md` — 开发验收的唯一依据
- `docs/02-测试用例.md` — 六组测试用例
- `docs/03-项目案例复盘.md` / `项目案例复盘.html` — 完整产研复盘
- `CHANGELOG.md` — 版本变更池
