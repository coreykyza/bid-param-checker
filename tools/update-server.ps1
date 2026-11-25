# bid-param-checker one-click server update (v2.9.1+)
# On the Windows server, paste ONE short line into PowerShell:
#   iex (iwr 'https://cdn.jsdelivr.net/gh/coreykyza/bid-param-checker@main/tools/update-server.ps1' -UseBasicParsing).Content
#
# Why this exists: pasting a long multi-line command into the PowerShell window
# gets wrapped/truncated. This script is downloaded as a FILE first, then run,
# so only the short one-liner above ever touches the console.
# Why jsDelivr CDN: the Aliyun ECS in mainland China often hangs forever on
# GitHub's raw domain. jsDelivr's CN nodes are reachable from mainland ECS.
$ErrorActionPreference = 'Stop'
$dir = 'C:\bidcheck'
$base = 'https://cdn.jsdelivr.net/gh/coreykyza/bid-param-checker@main'

Write-Host '[1/5] Stopping old server...'
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*server.py*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 800

Write-Host '[2/5] Downloading server.py + index.html...'
Invoke-WebRequest "$base/server.py" -OutFile "$dir\server.py" -UseBasicParsing
Invoke-WebRequest "$base/index.html" -OutFile "$dir\index.html" -UseBasicParsing

Write-Host '[3/5] Removing stale pool config from .env (built-in pool takes over)...'
$envFile = Join-Path $dir '.env'
if (Test-Path $envFile) {
  $kept = Get-Content $envFile | Where-Object {
    $_ -notmatch '^\s*LLM_MODEL_POOL\s*=' -and $_ -notmatch '^\s*LLM_VERIFY_POOL\s*='
  }
  # UTF8 without BOM - a BOM would corrupt the first key name in .env
  [System.IO.File]::WriteAllLines($envFile, $kept, (New-Object System.Text.UTF8Encoding($false)))
}

Write-Host '[4/5] Starting server...'
Start-Process 'C:\Program Files\Python312\python.exe' -ArgumentList 'server.py' -WorkingDirectory $dir -WindowStyle Hidden
Start-Sleep -Seconds 2

Write-Host '[5/5] Health check:'
$h = Invoke-RestMethod 'http://127.0.0.1:8765/health' -UseBasicParsing
$h | ConvertTo-Json -Depth 5
Write-Host ''
Write-Host ('route=' + $h.route + '  active_model=' + $h.model + '  dead=' + ($h.dead_models -join ','))
