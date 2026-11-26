# One-time installer for the production auto-sync.
# Downloads auto-update.ps1 from the CDN mirror, seeds the version pointer with the
# currently deployed commit, runs one sync cycle, and registers a Windows scheduled
# task that re-runs the sync every 5 minutes. Run once in an elevated PowerShell.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$dir  = 'C:\bidcheck'
$sha  = 'fde77104351750c03bffb685da9f29d87340336d'
$base = 'https://cdn.jsdmirror.com/gh/coreykyza/bid-param-checker'
$dst  = Join-Path $dir 'auto-update.ps1'

Write-Host '1/4 downloading auto-update.ps1 ...'
Invoke-WebRequest -Uri "$base@$sha/deploy/auto-update.ps1" -OutFile $dst -UseBasicParsing -TimeoutSec 30
if ((Get-Item $dst).Length -lt 500) { Write-Host 'FAIL: script download too small'; exit 1 }

Write-Host '2/4 seeding version pointer with currently deployed SHA ...'
Set-Content -Path (Join-Path $dir '.prod_sha') -Value $sha -Encoding ASCII

Write-Host '3/4 running one sync cycle (should be a no-op) ...'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $dst
Write-Host "   prod pointer now: $((Get-Content (Join-Path $dir '.prod_sha') -Raw).Trim())"

Write-Host '4/4 registering scheduled task BidParamAutoUpdate (every 5 minutes) ...'
schtasks /Create /TN BidParamAutoUpdate /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File C:\bidcheck\auto-update.ps1" /SC MINUTE /MO 5 /F /RL HIGHEST

Write-Host ''
Write-Host 'DONE. From now on the server updates its own frontend within minutes of a release.'
schtasks /Query /TN BidParamAutoUpdate
