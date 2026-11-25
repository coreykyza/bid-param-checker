#!/usr/bin/env python3
"""v2.0 验收检查：按 docs/01-需求基线.md 的 5 条验收标准核对导出的 Excel。

用法：/tmp/bidvenv/bin/python tools/验收检查.py output/xxx.xlsx
"""
import re
import sys
import zipfile

from openpyxl import load_workbook

path = sys.argv[1] if len(sys.argv) > 1 else "output/v2.0全量核验结果.xlsx"
ws = load_workbook(path).active

z = zipfile.ZipFile(path)
sheet_xml = z.read("xl/worksheets/sheet1.xml").decode()

# 从 XML 取 A 列富文本的红色片段（负偏离/待确认应标红在这里）
a_red = {}
# 用 XML 解析而非正则：空单元格是自闭合 <c r="A29" .../>，
# 正则极易跨行吞掉后续单元格导致行号错位（曾误判"多标29/漏标31"）。
import xml.etree.ElementTree as ET
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
try:
    root = ET.fromstring(sheet_xml)
    for c in root.iter(NS + "c"):
        ref = c.get("r") or ""
        if not ref.startswith("A"):
            continue
        try:
            row_no = int(ref[1:])
        except ValueError:
            continue
        if "FFC00000" in ET.tostring(c, encoding="unicode"):
            a_red[row_no] = True
except Exception as e:
    print(f"XML 解析失败，标红校验跳过：{e}")

fails = []
rows = []
for r in range(2, ws.max_row + 1):
    c = ws.cell(r, 3).value
    if not c:
        continue
    text = str(c)
    a = str(ws.cell(r, 1).value or "")
    rows.append((r, text, a))

print(f"文件：{path}")
print(f"有结论的行数：{len(rows)}\n")

# ---- 标准1：统计行四个数字之和 == 共N项的 N ----
print("【验收1】统计自洽（四数之和 == 总项数）")
bad1 = []
for r, text, a in rows:
    m = re.search(r"共(\d+)项：(.+)", text)
    if not m:
        bad1.append((r, "无统计行"))
        continue
    total = int(m.group(1))
    nums = [int(x) for x in re.findall(r"/?(\d+)", m.group(2))]
    parts = m.group(2).split("/")
    counts = [int(p.split("负偏离")[-1] if "负偏离" in p else
                  p.split("待确认")[-1] if "待确认" in p else
                  p.split("匹配")[-1] if "匹配" in p else
                  p.split("正偏离")[-1]) for p in parts]
    if sum(counts) != total:
        bad1.append((r, f"共{total}项 但 明细合计 {sum(counts)} ({counts})"))
if bad1:
    for r, why in bad1:
        print(f"  ✗ 行{r}: {why}")
    fails.append("验收1 统计自洽")
else:
    print("  ✓ 全部通过")

# ---- 标准2：统计行数字 == 明细实际行数 ----
print("\n【验收2】统计数字 == 明细行数")
bad2 = []
for r, text, a in rows:
    m = re.search(r"共(\d+)项：(.+)", text)
    if not m:
        continue
    parts = m.group(2).split("/")
    stat = {}
    for p in parts:
        for k in ("负偏离", "待确认", "匹配", "正偏离"):
            if p.startswith(k):
                stat[k] = int(p[len(k):])
    # 实际明细
    neg_block = re.search(r"负偏离：\n([\s\S]*?)(?:\n\n待确认：|\Z)", text)
    unc_block = re.search(r"待确认：\n([\s\S]*)$", text)
    real_neg = len([l for l in (neg_block.group(1).split("\n") if neg_block else []) if l.strip()])
    real_unc = len([l for l in (unc_block.group(1).split("\n") if unc_block else []) if l.strip()])
    if stat.get("负偏离", 0) != real_neg:
        bad2.append((r, f"负偏离统计{stat.get('负偏离',0)} != 明细{real_neg}"))
    if stat.get("待确认", 0) != real_unc:
        bad2.append((r, f"待确认统计{stat.get('待确认',0)} != 明细{real_unc}"))
if bad2:
    for r, why in bad2:
        print(f"  ✗ 行{r}: {why}")
    fails.append("验收2 统计与明细一致")
else:
    print("  ✓ 全部通过")

# ---- 标准3：明细里的序号能在 A 列原文找到 ----
print("\n【验收3】序号严格同步招标原文")
bad3 = []
seq_re = re.compile(r"【([^】]+)】")
for r, text, a in rows:
    for block in re.findall(r"(?:负偏离|待确认)：\n([\s\S]*?)(?=\n\n(?:负偏离|待确认)：|\Z)", text):
        for line in block.split("\n"):
            if not line.strip():
                continue
            m = seq_re.search(line)
            if not m:
                continue  # 无序号条目不校验
            seq = m.group(1)
            if seq not in a:
                bad3.append((r, seq))
if bad3:
    for r, seq in bad3[:10]:
        print(f"  ✗ 行{r}: 序号『{seq}』在 A 列原文中找不到")
    fails.append("验收3 序号同步")
else:
    print("  ✓ 全部通过")

# ---- 标准4：A 列标红行集合 == C 列部分满足行集合 ----
print("\n【验收4】A 列标红 == C 列部分满足")
part_rows = {r for r, text, a in rows if "部分满足" in text.split("\n")[0]}
all_rows = {r for r, text, a in rows}
red_rows = set(a_red)
if red_rows == part_rows:
    print(f"  ✓ 一致（{len(red_rows)} 行）")
else:
    print(f"  ✗ 标红 {sorted(red_rows)}")
    print(f"    部分满足 {sorted(part_rows)}")
    print(f"    多标 {sorted(red_rows - part_rows)} / 漏标 {sorted(part_rows - red_rows)}")
    fails.append("验收4 标红一致")

# ---- 标准5：全部满足行无明细 ----
print("\n【验收5】全部满足行不出现明细")
bad5 = []
for r, text, a in rows:
    if "全部满足" in text and ("负偏离：" in text or "待确认：" in text):
        bad5.append(r)
if bad5:
    print(f"  ✗ 行{bad5} 标全部满足却有明细")
    fails.append("验收5 全部满足无明细")
else:
    print("  ✓ 全部通过")

# ---- 汇总 ----
print("\n" + "=" * 46)
if fails:
    print("不通过：" + "、".join(fails))
    sys.exit(1)
print("全部 5 条验收标准通过")
