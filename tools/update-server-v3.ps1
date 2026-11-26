# bid-param-checker v3.0.0 server update - multi-provider routing (Volc + Bailian)
# Paste ONE short line into PowerShell on the Windows ECS:
#   iex (iwr 'https://cdn.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.0.0/tools/update-server-v3.ps1' -UseBasicParsing).Content
$ErrorActionPreference = 'Stop'
$dir = 'C:\bidcheck'
$base = 'https://cdn.jsdelivr.net/gh/coreykyza/bid-param-checker@v3.0.0'

Write-Host '[1/5] Stopping old server...'
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*server.py*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-Sleep -Milliseconds 800

Write-Host '[2/5] Downloading server.py + index.html...'
Invoke-WebRequest "$base/server.py" -OutFile "$dir\server.py" -UseBasicParsing
Invoke-WebRequest "$base/index.html" -OutFile "$dir\index.html" -UseBasicParsing

Write-Host '[3/5] Updating .env (multi-provider pools + Bailian key)...'
$envFile = Join-Path $dir '.env'
$lines = @()
if (Test-Path $envFile) { $lines = Get-Content $envFile }
# Keep LLM_BAILIAN_API_KEY and ACCESS_TOKEN from existing .env (never store keys in public scripts).
$dropRegex = '^\s*(LLM_MODEL|LLM_BASE_URL|LLM_THINKING|LLM_VERIFY_MODEL|LLM_VERIFY_POOL|LLM_MODEL_POOL|LLM_BAILIAN_BASE_URL|LLM_BAILIAN_THINKING|LLM_BAILIAN_KIMI_THINKING)\s*='
$kept = $lines | Where-Object { $_ -notmatch $dropRegex }
$add = @(
  'LLM_MODEL=deepseek-v4-1-flash-economy-261017',
  'LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3',
  'LLM_THINKING=disabled',
  'LLM_BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1',
  'LLM_BAILIAN_THINKING=disabled',
  'LLM_BAILIAN_KIMI_THINKING=kimi',
  'LLM_MODEL_POOL=bailian:deepseek-v4.1-flash-1017,bailian_kimi:kimi-k3.1-pro,bailian:qwen4-max,deepseek-v4-1-flash-economy-261017,deepseek-v4-flash-ga-260731,glm-5-3-flash-260828,deepseek-v4-pro-ga-260813,glm-5-2-260617,doubao-seed-evolving',
  'LLM_VERIFY_MODEL=doubao-seed-evolving',
  'LLM_VERIFY_POOL=doubao-seed-evolving,bailian:qwen4-max,deepseek-v4-pro-ga-260813,glm-5-3-flash-260828,glm-5-2-260617'
)
$all = @($kept) + $add
[System.IO.File]::WriteAllLines($envFile, $all, (New-Object System.Text.UTF8Encoding($false)))
Write-Host ('  .env lines: ' + $all.Count + ' (ACCESS_TOKEN + LLM_BAILIAN_API_KEY preserved if present)')
if (-not ($all | Where-Object { $_ -match '^\s*LLM_BAILIAN_API_KEY\s*=\s*sk-' })) {
  Write-Host 'WARNING: no LLM_BAILIAN_API_KEY in .env - Bailian models will fail. Add it manually before using.'
}

Write-Host '[4/5] Starting server...'
Start-Process 'C:\Program Files\Python312\python.exe' -ArgumentList 'server.py' -WorkingDirectory $dir -WindowStyle Hidden
Start-Sleep -Seconds 2

Write-Host '[5/5] Health check:'
$h = Invoke-RestMethod 'http://127.0.0.1:8765/health' -UseBasicParsing
$h | ConvertTo-Json -Depth 5
Write-Host ''
Write-Host ('route=' + $h.route + '  pool=' + @($h.model_pool).Count + '  verify=' + @($h.verify_pool).Count + '  extra=' + ($h.providers.extra -join ','))
