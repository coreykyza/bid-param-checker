# v1.x ~ v2.2 提交历史摘要

> 来源：旧 git 仓库（含密钥，已于 2026-11-25 移入废纸篓）
> 本文件仅保留**提交信息与文件名**，不含任何文件内容，可安全留存。
> 完整的过程性内容见 `CHANGELOG.md` 与 `03-项目案例复盘.md`。

## 提交时间线

```
e252679  11-24 14:24  feat: 招投标参数对照工具 v1.0
0631424  11-24 14:24  feat: 招投标参数对照工具 v1.0
d34b70f  11-24 14:51  fix(v1.1): 用户实测反馈修复
4607110  11-24 14:51  fix(v1.1): 用户实测反馈修复
4edcc62  11-24 16:36  fix(v1.2): 本地确定性判定 + 可读性
35e9973  11-24 16:36  fix(v1.2): 本地确定性判定 + 可读性
6cc3c72  11-24 17:01  feat(v1.3): 数值方向/二级序号/局部高亮/无对应项
43ac114  11-24 17:01  feat(v1.3): 数值方向/二级序号/局部高亮/无对应项
f0857e4  11-24 17:17  fix(v1.4): 正偏离误报与高亮缺失
81ccb1b  11-24 17:17  fix(v1.4): 正偏离误报与高亮缺失
860d326  11-25 10:33  add: 双击启动脚本，服务挂了自恢复
f1f1def  11-25 10:33  add: 双击启动脚本，服务挂了自恢复
8095ad8  11-25 13:12  feat(v2.0): 按需求文档重做为逐条四态判定
213e97e  11-25 13:12  feat(v2.0): 按需求文档重做为逐条四态判定
d34f0ce  11-25 14:10  fix(v2.0): 本地裁决三处关键修正
38430e1  11-25 14:10  fix(v2.0): 本地裁决三处关键修正
0567b00  11-25 15:37  feat(v2.1): 型号参数库 + 服务守护 + 命令行回归工具
2fae673  11-25 15:37  feat(v2.1): 型号参数库 + 服务守护 + 命令行回归工具
85c1609  11-25 15:57  feat(v2.2): 提速2倍 + 模型可切换
c9a9ff6  11-25 15:57  feat(v2.2): 提速2倍 + 模型可切换
1802592  11-25 16:00  feat(v2.3): 切换火山引擎DeepSeek, 264s→6.6s
4cb07dd  11-25 16:00  feat(v2.3): 切换火山引擎DeepSeek, 264s→6.6s
3017fd3  11-25 16:00  fix: .env 备份文件误入版本控制, 已加入 .gitignore
42649d2  11-25 16:00  fix: .env 备份文件误入版本控制, 已加入 .gitignore
c9b6568  11-25 16:01  chore: .env.example 去掉真实key, 改纯占位符
```

## 各提交涉及的变更文件

### e252679  feat: 招投标参数对照工具 v1.0
A · .gitignore
A · CHANGELOG.md
A · README.md
A · design/design-tokens.md
A · "docs/01-\351\234\200\346\261\202\345\237\272\347\272\277.md"
A · "docs/02-\346\265\213\350\257\225\347\224\250\344\276\213.md"
A · index.html
A · output/.gitkeep
A · server.py
A · tests/over_limit_101.xlsx
A · tests/sample_bid.xlsx
A · vendor/xlsx.full.min.js

### 0631424  feat: 招投标参数对照工具 v1.0
A · .env.example
A · .gitignore
A · CHANGELOG.md
A · README.md
A · design/design-tokens.md
A · "docs/01-\351\234\200\346\261\202\345\237\272\347\272\277.md"
A · "docs/02-\346\265\213\350\257\225\347\224\250\344\276\213.md"
A · index.html
A · output/.gitkeep
A · server.py
A · tests/over_limit_101.xlsx
A · tests/sample_bid.xlsx
A · vendor/xlsx.full.min.js

### d34b70f  fix(v1.1): 用户实测反馈修复
M · CHANGELOG.md
M · README.md
M · index.html
M · server.py
A · tests/real_upload.xlsx

### 4607110  fix(v1.1): 用户实测反馈修复
M · CHANGELOG.md
M · README.md
M · index.html
M · server.py
A · tests/real_upload.xlsx

### 4edcc62  fix(v1.2): 本地确定性判定 + 可读性
M · CHANGELOG.md
M · README.md
M · index.html
M · server.py

### 35e9973  fix(v1.2): 本地确定性判定 + 可读性
M · CHANGELOG.md
M · README.md
M · index.html
M · server.py

### 6cc3c72  feat(v1.3): 数值方向/二级序号/局部高亮/无对应项
M · CHANGELOG.md
M · README.md
M · index.html
A · vendor/jszip.min.js

### 43ac114  feat(v1.3): 数值方向/二级序号/局部高亮/无对应项
M · CHANGELOG.md
M · README.md
M · index.html
A · vendor/jszip.min.js

### f0857e4  fix(v1.4): 正偏离误报与高亮缺失
M · CHANGELOG.md
M · README.md
M · index.html

### 81ccb1b  fix(v1.4): 正偏离误报与高亮缺失
M · CHANGELOG.md
M · README.md
M · index.html

### 860d326  add: 双击启动脚本，服务挂了自恢复
A · "\345\220\257\345\212\250\345\267\245\345\205\267.command"

### f1f1def  add: 双击启动脚本，服务挂了自恢复
A · "\345\220\257\345\212\250\345\267\245\345\205\267.command"

### 8095ad8  feat(v2.0): 按需求文档重做为逐条四态判定
M · CHANGELOG.md
M · README.md
M · "docs/01-\351\234\200\346\261\202\345\237\272\347\272\277.md"
M · "docs/02-\346\265\213\350\257\225\347\224\250\344\276\213.md"
M · index.html
A · "tools/\351\252\214\346\224\266\346\243\200\346\237\245.py"

### 213e97e  feat(v2.0): 按需求文档重做为逐条四态判定
M · CHANGELOG.md
M · README.md
M · "docs/01-\351\234\200\346\261\202\345\237\272\347\272\277.md"
M · "docs/02-\346\265\213\350\257\225\347\224\250\344\276\213.md"
M · index.html
A · "tools/\351\252\214\346\224\266\346\243\200\346\237\245.py"

### d34f0ce  fix(v2.0): 本地裁决三处关键修正
M · CHANGELOG.md
M · index.html

### 38430e1  fix(v2.0): 本地裁决三处关键修正
M · CHANGELOG.md
M · index.html

### 0567b00  feat(v2.1): 型号参数库 + 服务守护 + 命令行回归工具
M · CHANGELOG.md
M · README.md
A · data/hw-matcher.js
A · data/hw-specs.js
M · index.html
A · logs/proxy.log
A · "tools/xlsx\350\275\254json.py"
A · "tools/\345\233\236\345\275\222\351\252\214\350\257\201.js"
A · "tools/\347\224\237\346\210\220\347\273\223\346\236\234Excel.py"
M · "tools/\351\252\214\346\224\266\346\243\200\346\237\245.py"
M · "\345\220\257\345\212\250\345\267\245\345\205\267.command"
A · "\345\256\211\350\243\205\350\207\252\345\220\257\346\234\215\345\212\241.command"

### 2fae673  feat(v2.1): 型号参数库 + 服务守护 + 命令行回归工具
M · CHANGELOG.md
M · README.md
A · data/hw-matcher.js
A · data/hw-specs.js
M · index.html
A · logs/proxy.log
A · "tools/xlsx\350\275\254json.py"
A · "tools/\345\233\236\345\275\222\351\252\214\350\257\201.js"
A · "tools/\347\224\237\346\210\220\347\273\223\346\236\234Excel.py"
M · "tools/\351\252\214\346\224\266\346\243\200\346\237\245.py"
M · "\345\220\257\345\212\250\345\267\245\345\205\267.command"
A · "\345\256\211\350\243\205\350\207\252\345\220\257\346\234\215\345\212\241.command"

### 85c1609  feat(v2.2): 提速2倍 + 模型可切换
M · CHANGELOG.md
M · README.md
M · index.html
A · logs/proxy.err.log
M · logs/proxy.log
M · server.py
M · "tools/\345\233\236\345\275\222\351\252\214\350\257\201.js"

### c9a9ff6  feat(v2.2): 提速2倍 + 模型可切换
M · .env.example
M · CHANGELOG.md
M · README.md
M · index.html
A · logs/proxy.err.log
M · logs/proxy.log
M · server.py
M · "tools/\345\233\236\345\275\222\351\252\214\350\257\201.js"

### 1802592  feat(v2.3): 切换火山引擎DeepSeek, 264s→6.6s
M · CHANGELOG.md
M · README.md
M · data/hw-matcher.js
M · index.html
M · logs/proxy.log
M · "tools/\345\233\236\345\275\222\351\252\214\350\257\201.js"

### 4cb07dd  feat(v2.3): 切换火山引擎DeepSeek, 264s→6.6s
A · .env.zhipu.bak
M · CHANGELOG.md
M · README.md
M · data/hw-matcher.js
M · index.html
M · logs/proxy.log
M · "tools/\345\233\236\345\275\222\351\252\214\350\257\201.js"

### 3017fd3  fix: .env 备份文件误入版本控制, 已加入 .gitignore
D · .env.zhipu.bak
M · .gitignore

### 42649d2  fix: .env 备份文件误入版本控制, 已加入 .gitignore
M · .gitignore

### c9b6568  chore: .env.example 去掉真实key, 改纯占位符
M · .env.example
