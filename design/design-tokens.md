# Design Tokens — 招投标参数对照工具

视觉基线：Element Plus 风格，浅色主题。所有样式在 `index.html` 的 `:root` 中以 CSS 变量定义，前端不得静默漂移。

## Color

| Token | 值 | 用途 |
|---|---|---|
| --primary | #2563eb | 主按钮、步骤圆点、激活态 |
| --primary-hover | #1d4ed8 | 主按钮 hover |
| --primary-soft | #eff6ff | 标签底色、拖拽 hover |
| --bg | #f5f7fa | 页面背景 |
| --panel | #ffffff | 卡片面板 |
| --border | #e4e7ed | 边框 |
| --text | #1f2937 | 主文本 |
| --muted | #6b7280 | 次要文本 |
| --red / --red-bg | #dc2626 / #fef2f2 | 负偏离（红底 #FFC7CE + 深红字 #9C0006） |
| --green / --green-bg | #059669 / #ecfdf5 | 正偏离 |
| --amber / --amber-bg | #d97706 / #fffbeb | 待确认 / 演示模式提示 |

## Typography
- 字体栈：-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif
- 标题 22px / 700；卡片标题 14px / 600；正文 12px；统计数字 20px / 700

## Layout & Shape
- 主容器 max-width 1240px，栅格 340px + 1fr（<900px 折叠为单列）
- 圆角 10px（卡片）/ 8px（按钮、内框图）/ 20px（徽标）
- 阴影 0 1px 3px rgba(0,0,0,.06), 0 8px 24px rgba(0,0,0,.04)

## Excel 标红规范（写回文件）
- 负偏离行 C 单元格：fill fgColor `FFC7CE`，font color `9C0006` + bold，wrapText
- 其余行 C 单元格：白底，深灰字
- C 列表头：蓝底 `2563EB` + 白字加粗；列宽 72
