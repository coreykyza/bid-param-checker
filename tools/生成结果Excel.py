#!/usr/bin/env python3
"""把 回归验证.js 产出的 results.json 写成带格式的核验结果 Excel。

- C 列写结论（首行"结论｜共N项：…"，下方只列负偏离与待确认明细）
- A 列把负偏离/待确认条目文字标红加粗（富文本 inlineStr）
- 保留 A/B 原始列宽与换行

用法：python3 tools/生成结果Excel.py <源xlsx> <results.json> <输出xlsx>
"""
import json
import re
import shutil
import sys
import zipfile

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

src = sys.argv[1]
results_file = sys.argv[2]
dst = sys.argv[3]

results = json.load(open(results_file, encoding="utf-8"))
results.sort(key=lambda r: r["row"])

# ---------- 1. 用 openpyxl 写 C 列 ----------
wb = load_workbook(src)
ws = wb.active

thin = Side(style="thin", color="E4E7ED")
border = Border(top=thin, bottom=thin, left=thin, right=thin)
wrap_top = Alignment(wrap_text=True, vertical="top", horizontal="left")

if ws["C1"].value in (None, ""):
    ws["C1"] = "核验结论"
    ws["C1"].font = Font(name="微软雅黑", bold=True, color="FFFFFF")
    ws["C1"].fill = PatternFill("solid", fgColor="2563EB")
    ws["C1"].alignment = Alignment(horizontal="center", vertical="center")

for r in results:
    cell = ws.cell(r["row"], 3)
    cell.value = r["cText"]
    cell.font = Font(name="微软雅黑", size=9, color="1F2937")
    cell.alignment = wrap_top
    cell.border = border

ws.column_dimensions["C"].width = 60
wb.save(dst)

# ---------- 2. 后处理：A 列标红（富文本 inlineStr） ----------
XML_ESC = lambda s: (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def run(text, hot):
    t = XML_ESC(text)
    if hot:
        rpr = '<rPr><rFont val="微软雅黑"/><b val="1"/><color rgb="FFC00000"/><sz val="9"/></rPr>'
    else:
        rpr = '<rPr><rFont val="微软雅黑"/><sz val="9"/></rPr>'
    return f'<r>{rpr}<t xml:space="preserve">{t}</t></r>'


def rich_runs(text, needles):
    """把 text 按 needles 切成高亮/普通 run"""
    if not needles:
        return run(text, False)
    cand = [n for n in needles if n and n in text]
    if not cand:
        return run(text, False)
    cand.sort(key=len, reverse=True)
    out = []
    i = 0
    while i < len(text):
        hit = None
        for n in cand:
            if text.startswith(n, i):
                hit = n
                break
        if hit:
            out.append(run(text[i:i + len(hit)], True))
            i += len(hit)
        else:
            nxt = len(text)
            for n in cand:
                p = text.find(n, i)
                if p >= 0:
                    nxt = min(nxt, p)
            out.append(run(text[i:nxt], False))
            i = nxt
    return "".join(out)


# 从源文件取 A 列原文
src_ws = load_workbook(src).active

with zipfile.ZipFile(dst) as z:
    sheet_name = [n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)][0]
    xml = z.read(sheet_name).decode("utf-8")
    all_items = {n: z.read(n) for n in z.namelist()}

red_rows = []
for r in results:
    bad = [it for it in r["items"] if it["status"] in ("negative", "uncertain")]
    if not bad:
        continue
    a_raw = src_ws.cell(r["row"], 1).value
    if a_raw is None:
        continue
    a_text = str(a_raw)
    flat = re.sub(r"\s+", " ", a_text)

    needles = []
    for it in bad:
        body = re.sub(r"\s+", " ", str(it.get("text") or "")).strip()
        if not body:
            continue
        if body in flat:
            needles.append(body)
        elif len(body) > 20 and body[:20] in flat:
            needles.append(body[:20])
        elif len(body) >= 8 and body[:8] in flat:
            needles.append(body[:8])
    if not needles:
        continue

    inline = "<is>" + rich_runs(a_text, needles) + "</is>"
    pat = re.compile(r'<c r="A%d"[^>]*>[\s\S]*?</c>' % r["row"])
    m = pat.search(xml)
    if not m:
        continue
    sm = re.search(r' s="(\d+)"', m.group(0))
    s_attr = f' s="{sm.group(1)}"' if sm else ""
    xml = pat.sub(f'<c r="A{r["row"]}"{s_attr} t="inlineStr">{inline}</c>', xml, count=1)
    red_rows.append(r["row"])

with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
    for name, data in all_items.items():
        if name == sheet_name:
            data = xml.encode("utf-8")
        z.writestr(name, data)

print(f"已写入 {dst}")
print(f"A 列标红行：{red_rows}（共 {len(red_rows)} 行）")
