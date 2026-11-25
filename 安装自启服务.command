#!/bin/bash
# 招投标参数对照工具 — 安装开机自启 + 崩溃自动重启（launchd 守护）
#
# 为什么要装这个：
#   手动启动的进程会随终端关闭而退出，或被系统回收，之后 http://localhost:8765 就打不开了。
#   launchd 守护能保证：开机自动启动、进程挂了自动拉起、退出登录再登录也在。
#
# 用法：在「终端」里执行一次
#   bash "/Users/chuck/WorkBuddy/项目1/bid-param-checker/安装自启服务.command"
#
# 卸载：
#   launchctl bootout gui/$(id -u)/com.workbuddy.bidchecker

DIR="/Users/chuck/WorkBuddy/项目1/bid-param-checker"
PLIST="$HOME/Library/LaunchAgents/com.workbuddy.bidchecker.plist"
UID_NUM=$(id -u)

echo "==> 停止已有实例"
pkill -f "$DIR/server.py" 2>/dev/null
sleep 1

echo "==> 写入 launchd 配置"
mkdir -p "$HOME/Library/LaunchAgents" "$DIR/logs"

cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.workbuddy.bidchecker</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$DIR/server.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$DIR</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ThrottleInterval</key>
  <integer>10</integer>
  <key>StandardOutPath</key>
  <string>$DIR/logs/proxy.log</string>
  <key>StandardErrorPath</key>
  <string>$DIR/logs/proxy.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PYTHONUNBUFFERED</key>
    <string>1</string>
  </dict>
</dict>
</plist>
PLIST_EOF

plutil -lint "$PLIST" >/dev/null || { echo "plist 格式错误"; exit 1; }

echo "==> 注册服务"
launchctl bootout "gui/$UID_NUM/com.workbuddy.bidchecker" 2>/dev/null
launchctl bootstrap "gui/$UID_NUM" "$PLIST" 2>&1 | head -3
launchctl enable "gui/$UID_NUM/com.workbuddy.bidchecker" 2>/dev/null

echo "==> 等待服务就绪"
for i in $(seq 1 20); do
  if curl -s -m 1 http://127.0.0.1:8765/health > /dev/null 2>&1; then
    echo "✓ 服务已就绪：http://localhost:8765"
    echo "✓ 已设为开机自启，进程挂了会自动重启"
    open "http://localhost:8765"
    exit 0
  fi
  sleep 0.5
done

echo "✗ 启动失败，请查看日志：$DIR/logs/proxy.err.log"
tail -20 "$DIR/logs/proxy.err.log" 2>/dev/null
exit 1
