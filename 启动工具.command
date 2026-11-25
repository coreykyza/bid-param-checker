#!/bin/bash
# 招投标参数对照工具 — 双击启动
#
# 做三件事：
#   1. 清理残留进程
#   2. 启动本地代理（后台脱离当前终端）
#   3. 拉起一个看门狗，检测到服务挂了自动重启（防系统回收）

DIR="/Users/chuck/WorkBuddy/项目1/bid-param-checker"
cd "$DIR" || exit 1
mkdir -p logs

echo "正在清理残留进程..."
pkill -f "$DIR/server.py" 2>/dev/null
pkill -f "bid-checker-watchdog" 2>/dev/null
sleep 1

echo "正在启动服务..."
nohup python3 server.py >> logs/proxy.log 2>&1 &
disown

# 看门狗：每 10 秒检查一次，挂了重新拉起
nohup bash -c '
while true; do
  sleep 10
  if ! curl -s -m 2 http://127.0.0.1:8765/health > /dev/null 2>&1; then
    cd "'"$DIR"'"
    nohup python3 server.py >> logs/proxy.log 2>&1 &
    echo "[$(date "+%H:%M:%S")] 看门狗已重启服务" >> logs/proxy.log
  fi
done
' >> logs/watchdog.log 2>&1 &
disown

# 等待就绪（最多 10 秒）
for i in $(seq 1 20); do
  if curl -s -m 1 http://127.0.0.1:8765/health > /dev/null 2>&1; then
    echo "服务已就绪：http://localhost:8765"
    open "http://localhost:8765"
    echo "（看门狗已启动，服务挂了会自动重启）"
    exit 0
  fi
  sleep 0.5
done

echo "启动失败，请查看日志：$DIR/logs/proxy.log"
tail -20 logs/proxy.log 2>/dev/null
exit 1
