# Bid-param-checker production frontend auto-sync  (v3, 2026-11-26)
#
# WHY: Reading the pointer from "@main/deploy/prod.txt" is BROKEN on this ECS.
#      Every CDN mirror caches @main for hours and ignores query-string cache
#      busters -> the server read a STALE SHA and even rolled index.html
#      BACKWARDS to v3.1.1 (badge still said v2.4). So neither the installed
#      badge nor the @main pointer is a reliable "latest version" signal.
#
# HOW (rollback-proof, no single point of failure):
#   "@<40-hex SHA>/index.html" and "@v3.2.X/index.html" (tag) are IMMUTABLE,
#   served instantly by all mirrors, and immune to the @main cache.
#     FAST PATH  : ask GitHub API for the live main SHA (1 request). If its
#                 index.html badge is newer than installed, install and exit.
#     FALLBACK  : enumerate a predictable range of version tags (v3.2.x /
#                 v3.3.x / v3.4.x) over the proven-reachable mirror, plus any
#                 @main pointer values, and pick the HIGHEST badge strictly
#                 newer than installed.
#   Version is parsed from the "vMAJOR.MINOR.PATCH" badge inside the file, so a
#   stale/bogus candidate can never overwrite a newer installed file.
#   index.html is static (FastAPI serves the file directly): NO restart needed.
#
# MAINTENANCE: when the version line passes v3.4.x, extend the tag ranges below.
# Release (agent side): commit index.html, then CREATE A TAG v3.2.X and push it.
$ErrorActionPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$dir     = 'C:\bidcheck'
$mirrors = @(
  'https://cdn.jsdmirror.com/gh/coreykyza/bid-param-checker',
  'https://fastly.jsdelivr.net/gh/coreykyza/bid-param-checker',
  'https://testingcf.jsdelivr.net/gh/coreykyza/bid-param-checker',
  'https://gcore.jsdelivr.net/gh/coreykyza/bid-param-checker',
  'https://cdn.jsdelivr.net/gh/coreykyza/bid-param-checker'
)
$shaFile = Join-Path $dir '.prod_sha'
$logFile = Join-Path $dir 'autoupdate.log'
$curFile = Join-Path $dir 'index.html'

function Get-BadgeVer([string]$path) {
  try {
    $txt = Get-Content $path -Raw -ErrorAction Stop
    if ($txt -match 'class="badge">v(\d+)\.(\d+)\.(\d+)') {
      return ([int]$Matches[1] * 10000 + [int]$Matches[2] * 100 + [int]$Matches[3])
    }
  } catch {}
  return 0
}
# Download "@<ref>/index.html", return @{ver,len,path,ref} or $null.
function Fetch-Pinned([string]$ref, [string[]]$hosts) {
  $safe = ($ref -replace '[^0-9a-zA-Z]', '_')
  $tmp = Join-Path $env:TEMP ("idx_" + $safe + ".html")
  foreach ($m in $hosts) {
    try {
      if (Test-Path $tmp) { Remove-Item $tmp -Force }
      Invoke-WebRequest -Uri "$m@$ref/index.html" -OutFile $tmp -UseBasicParsing -TimeoutSec 15
      if (-not (Test-Path $tmp)) { continue }
      $len = (Get-Item $tmp).Length
      if ($len -lt 50000) { continue }
      $head = (Get-Content $tmp -TotalCount 5) -join ' '
      if ($head -notmatch '<html') { continue }
      $ver = Get-BadgeVer $tmp
      if ($ver -le 0) { continue }
      return @{ ver = $ver; len = $len; path = $tmp; ref = $ref }
    } catch {}
  }
  return $null
}

$curVer = 0
if (Test-Path $curFile) { $curVer = Get-BadgeVer $curFile }
$best = $null

# ---- FAST PATH: live main SHA from GitHub API (may be blocked on CN ECS) ----
try {
  $api = Invoke-RestMethod -Uri 'https://api.github.com/repos/coreykyza/bid-param-checker/commits/main' `
           -Headers @{ 'User-Agent' = 'bidcheck-autoupdate' } -TimeoutSec 8
  if ($api.sha -match '^[0-9a-f]{40}$') {
    $c = Fetch-Pinned $api.sha $mirrors
    if ($c -and $c.ver -gt $curVer) { $best = $c }
  }
} catch {}

# ---- FALLBACK: predictable tags + @main pointers, pick highest badge ----
if (-not $best) {
  $refs = New-Object System.Collections.Generic.List[string]
  for ($p = 0; $p -le 20; $p++) { $refs.Add("v3.2.$p") }
  for ($p = 0; $p -le 6;  $p++) { $refs.Add("v3.3.$p") }
  for ($p = 0; $p -le 6;  $p++) { $refs.Add("v3.4.$p") }
  $t = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  foreach ($m in $mirrors) {
    try {
      $r = Invoke-WebRequest -Uri "$m@main/deploy/prod.txt?t=$t" -UseBasicParsing -TimeoutSec 8
      $c = ($r.Content).Trim()
      if ($c -match '^(v\d+\.\d+\.\d+|[0-9a-f]{40})$') { $refs.Add($c) }
    } catch {}
  }
  if (Test-Path $shaFile) {
    $c = (Get-Content $shaFile -Raw).Trim()
    if ($c -match '^(v\d+\.\d+\.\d+|[0-9a-f]{40})$') { $refs.Add($c) }
  }
  $refs = @($refs | Select-Object -Unique)
  foreach ($ref in $refs) {
    # tags only hit the proven-reachable mirror (low request count); SHAs try all
    $hosts = if ($ref.StartsWith('v')) { @($mirrors[0]) } else { $mirrors }
    $c = Fetch-Pinned $ref $hosts
    if ($c -and $c.ver -gt $curVer -and (-not $best -or $c.ver -gt $best.ver)) { $best = $c }
  }
}

# Nothing strictly newer -> do NOT overwrite (rollback-proof).
if (-not $best -or -not (Test-Path $best.path)) { exit 0 }

Copy-Item $best.path (Join-Path $dir 'index.html') -Force
Set-Content -Path $shaFile -Value $best.ref -Encoding ASCII
"$(Get-Date -Format 's') updated -> $($best.ref) (badge $($best.ver), $($best.len) bytes)" | Out-File $logFile -Append -Encoding ascii
