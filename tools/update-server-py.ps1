# bid-param-checker v3.2.9 后端更新（只更 server.py，绝不动 .env）
#
# 用途：v3.2.9 改了 server.py（provider 并发闸 + 限流熔断 + SetLimitExceeded 识别），
#   后端改动无法靠前端的自动同步脚本生效，必须在 Windows ECS 上手动执行一次。
#
# 用法：在服务器 PowerShell 里粘贴 ONE 行：
#   iex (iwr 'https://cdn.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.2.9/tools/update-server-py.ps1' -UseBasicParsing).Content
#
# 【重要】旧脚本 tools/update-server-v3.ps1 会重写 .env 的模型池（把 tf: 池冲成 bailian 池），
#   本脚本刻意不碰 .env —— 你的 key、模型池、访问口令全部原样保留。
$ErrorActionPreference = 'Stop'
$dir = 'C:\bidcheck'
$target = "$dir\server.py"

# 多镜像轮询（ECS 出站到 cdn.jsdelivr.net 曾被持续重置 → 首选 jsdmirror）
$mirrors = @(
  'https://cdn.jsdmirror.com/gh/coreykyza/bid-param-checker@v3.2.9/server.py',
  'https://cdn.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.2.9/server.py',
  'https://fastly.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.2.9/server.py',
  'https://testingcf.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.2.9/server.py'
)

Write-Host '[1/4] 备份现有 server.py ...'
if (Test-Path $target) {
  Copy-Item $target "$dir\server.py.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')" -Force
  Write-Host ('  已备份 → ' + (Get-ChildItem "$dir\server.py.bak_*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).Name)
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
    # 校验：字节数合理 + 含关键新代码（并发闸）+ 是 python 源码
    $txt = Get-Content $tmp -Raw -Encoding UTF8
    if ($len -gt 20000 -and $txt -like '*_provider_try_acquire*' -and $txt -like '*def do_POST*') {
      Write-Host ("  OK  {0}  ({1} 字节)" -f $m, $len)
      $ok = $true
      break
    } else {
      Write-Host ("  内容校验失败（{0} 字节，缺并发闸特征？）→ 换镜像" -f $len)
    }
  } catch {
    Write-Host ("  失败 {0} → {1}" -f $m, $_.Exception.Message)
  }
}
if (-not $ok) { throw '所有镜像均下载失败或校验不通过，已中止（未覆盖现有 server.py，服务仍在运行）' }

Write-Host '[3/4] 停止旧 python 进程 ...'
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*server.py*' } |
  ForEach-Object {
    Write-Host ('  stop PID ' + $_.ProcessId)
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }
Start-Sleep -Milliseconds 1200

Write-Host '[4/4] 覆盖并重启 ...'
Move-Item $tmp $target -Force
Write-Host ('  已安装 ' + (Get-Item $target).Length + ' 字节')
Start-Process -FilePath 'python' -ArgumentList 'server.py' -WorkingDirectory $dir -WindowStyle Hidden
Start-Sleep -Seconds 3

try {
  $h = Invoke-WebRequest 'http://127.0.0.1:8765/health' -UseBasicParsing -TimeoutSec 10
  Write-Host '  health 200 OK'
  Write-Host ('  并发闸配置: ' + ($h.Content | ConvertFrom-Json).provider_gate_config | ConvertTo-Json -Compress)
} catch {
  Write-Host ('  ⚠ health 探测失败：' + $_.Exception.Message + ' —— 请手动检查 C:\bidcheck 下的 python 进程')
}
Write-Host ''
Write-Host '完成。外部验证：'
Write-Host '  curl http://101.37.234.89:8765/health   （应看到 provider_gate_config / provider_gates）'
Write-Host '  然后打一发真实判定，看返回的 model 字段是否正常。'
