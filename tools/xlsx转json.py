#!/usr/bin/env python3
"""把核验用的 Excel 转成 rows.json（AB 列），供 tools/回归验证.js 使用。

用法：python3 tools/xlsx转json.py <源文件.xlsx> [输出.json]
"""
import json
import re
import sys

from openpyxl import load_workbook

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/rows.json"

ws = load_workbook(src).active
rows = []
for r in range(2, ws.max_row + 1):
    a = ws.cell(r, 1).value
    b = ws.cell(r, 2).value
    if a is None and b is None:
        continue
    a = str(a or "").strip()
    b = str(b or "").strip()
    if not a:
        continue
    # 跳过无实质内容的脏数据行：纯符号/单个字符（如只有一个"/"）
    substantive = re.sub(r"[\s/\\|、，,。.．·\-—_=+*#※☆★（）()\[\]【】]", "", a)
    if len(substantive) < 2:
        continue
    rows.append({"row": r, "a": a, "b": b})

with open(out, "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)

print(f"已导出 {len(rows)} 行 → {out}")
