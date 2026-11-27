# bid-param-checker v3.2.10 后端更新（只更 server.py，绝不动 .env）
#
# 用途：v3.2.9 改了 server.py（provider 并发闸 + 限流熔断 + SetLimitExceeded 识别），
#   后端改动无法靠前端的自动同步脚本生效，必须在 Windows ECS 上手动执行一次。
#
# 【怎么执行】不要用 iex(iwr...).Content —— CDN 用 application/octet-stream 返回，
#   PowerShell 的 .Content 是 byte[]，iex 会报「无法将 System.Byte[] 转换为 System.String」。
#   正确姿势（先落盘再执行）：
#     iwr 'https://cdn.jsdmirror.com/gh/coreykyza/bid-param-checker@v3.2.10/tools/update-server-py.ps1' -OutFile $env:TEMP\upd.ps1 -UseBasicParsing
#     powershell -ExecutionPolicy Bypass -File $env:TEMP\upd.ps1
#
# 【重要】旧脚本 tools/update-server-v3.ps1 会重写 .env 的模型池（把 tf: 池冲成 bailian 池），
#   本脚本刻意不碰 .env —— 你的 key、模型池、访问口令全部原样保留。
$ErrorActionPreference = 'Stop'
$dir = 'C:\bidcheck'
$target = "$dir\server.py"

if (-not (Test-Path $dir)) { throw "目录不存在：$dir" }

# ---- 先把 python 路径定死（旧脚本用的就是全路径，PATH 里可能没有 python） ----
$pyCandidates = @(
  'C:\Program Files\Python312\python.exe',
  'C:\Program Files\Python311\python.exe',
  'C:\Program Files\Python310\python.exe',
  'C:\Python312\python.exe',
  'C:\Python311\python.exe'
)
$py = $pyCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $py) {
  $cmd = Get-Command python -ErrorAction SilentlyContinue
  if ($cmd) { $py = $cmd.Source }
}
if (-not $py) { throw '找不到 python.exe（已试常见路径和 PATH），请手动确认后改脚本里的 $pyCandidates' }
Write-Host ("python: " + $py)

# 多镜像轮询（ECS 出站到 cdn.jsdelivr.net 曾被持续重置 → 首选 jsdmirror）
$mirrors = @(
  'https://cdn.jsdmirror.com/gh/coreykyza/bid-param-checker@v3.2.10/server.py',
  'https://cdn.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.2.10/server.py',
  'https://fastly.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.2.10/server.py',
  'https://testingcf.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.2.10/server.py'
)

Write-Host '[1/4] 备份现有 server.py ...'
if (Test-Path $target) {
  $bak = "$dir\server.py.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
  Copy-Item $target $bak -Force
  Write-Host ("  已备份 → " + (Split-Path $bak -Leaf))
} else {
  Write-Host '  无旧文件（首次安装），跳过备份'
}

Write-Host '[2/4] 下载新 server.py ...'
$tmp = "$env:TEMP\server.py.new"
$ok = $false
foreach ($m in $mirrors) {
  try {
    Invoke-WebRequest $m -OutFile $tmp -UseBasicParsing -TimeoutSec 25 -ErrorAction Stop
    $len = (Get-Item $tmp).Length
    # 校验：字节数合理 + 含关键新代码（并发闸 + 退避诊断）+ 是 python 源码
    $txt = Get-Content $tmp -Raw -Encoding UTF8
    if ($len -gt 20000 -and $txt -like '*_provider_try_acquire*' -and $txt -like '*last_route_errors*' -and $txt -like '*def do_POST*') {
      Write-Host ("  OK  {0}  ({1} 字节，含并发闸+退避诊断特征)" -f $m, $len)
      $ok = $true
      break
    } else {
      Write-Host ("  内容校验失败（{0} 字节，缺并发闸/退避特征）→ 换镜像" -f $len)
    }
  } catch {
    Write-Host ("  失败 {0} → {1}" -f $m, $_.Exception.Message)
  }
}
if (-not $ok) { throw '所有镜像均下载失败或校验不通过，已中止（未覆盖现有 server.py，服务仍在运行）' }

Write-Host '[3/4] 停止旧 python 进程 ...'
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -like '*server.py*' }
if (-not $procs) { Write-Host '  没有正在运行的 server.py（可能已停）' }
foreach ($p in $procs) {
  Write-Host ('  stop PID ' + $p.ProcessId)
  Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 1500

Write-Host '[4/4] 覆盖并重启 ...'
Move-Item $tmp $target -Force
Write-Host ('  已安装 ' + (Get-Item $target).Length + ' 字节')
Start-Process -FilePath $py -ArgumentList 'server.py' -WorkingDirectory $dir -WindowStyle Hidden
Start-Sleep -Seconds 4

try {
  $h = Invoke-WebRequest 'http://127.0.0.1:8765/health' -UseBasicParsing -TimeoutSec 10
  $j = $h.Content | ConvertFrom-Json
  Write-Host '  health 200 OK'
  if ($j.provider_gate_config) {
    Write-Host ('  并发闸：' + ($j.provider_gate_config | ConvertTo-Json -Compress))
    Write-Host '  ✅ 新版已生效（能读到 provider_gate_config 即证明 server.py 已换）'
  } else {
    Write-Host '  ⚠ health 里没有 provider_gate_config —— 可能是旧进程没停掉，检查端口占用'
  }
  if ($j.dead_models -and $j.dead_models.Count -gt 0) {
    Write-Host ('  当前拉黑模型：' + ($j.dead_models -join ', '))
  }
} catch {
  Write-Host ('  ⚠ health 探测失败：' + $_.Exception.Message + ' —— 请手动检查 C:\bidcheck 下的 python 进程')
}
Write-Host ''
Write-Host '完成。外网验证：'
Write-Host '  curl http://101.37.234.89:8765/health   （应看到 provider_gate_config / provider_gates）'
