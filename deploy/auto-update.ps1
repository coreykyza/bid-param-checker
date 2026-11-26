# Bid-param-checker production frontend auto-sync.
# Flow: read deploy/prod.txt (a commit SHA pointer) from CDN mirror -> if SHA changed,
# download index.html pinned to that exact SHA (immutable, no CDN cache issues) ->
# validate payload -> atomically replace C:\bidcheck\index.html.
# index.html is a static file served by FastAPI: replacing it needs NO service restart.
# Release process (agent side): commit index.html, push, then update deploy/prod.txt
# to the new commit SHA and push again. The server picks it up within minutes.
$ErrorActionPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$dir     = 'C:\bidcheck'
$mirrors = @(
  'https://cdn.jsdmirror.com/gh/coreykyza/bid-param-checker',
  'https://fastly.jsdelivr.net/gh/coreykyza/bid-param-checker',
  'https://testingcf.jsdelivr.net/gh/coreykyza/bid-param-checker',
  'https://gcore.jsdelivr.net/gh/coreykyza/bid-param-checker'
)
$shaFile = Join-Path $dir '.prod_sha'
$logFile = Join-Path $dir 'autoupdate.log'

$cur = ''
if (Test-Path $shaFile) { $cur = (Get-Content $shaFile -Raw).Trim() }

# 1) fetch the version pointer, first reachable mirror wins.
# Random query string busts the CDN cache for @main paths.
$t = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$new = $null
foreach ($m in $mirrors) {
  foreach ($suffix in @("?t=$t", "?t=$t-b")) {
    try {
      $r = Invoke-WebRequest -Uri "$m@main/deploy/prod.txt$suffix" -UseBasicParsing -TimeoutSec 20
      if ($r.StatusCode -eq 200) {
        $c = $r.Content.Trim()
        if ($c -match '^[0-9a-f]{40}$') { $new = $c; break }
      }
    } catch {}
  }
  if ($new) { break }
}
if (-not $new) { exit 0 }        # pointer unreachable -> keep current version
if ($new -eq $cur) { exit 0 }    # already up to date

# 2) download index.html pinned to the exact SHA
$tmp = Join-Path $env:TEMP 'idx_auto.html'
if (Test-Path $tmp) { Remove-Item $tmp -Force }
foreach ($m in $mirrors) {
  try {
    Invoke-WebRequest -Uri "$m@$new/index.html" -OutFile $tmp -UseBasicParsing -TimeoutSec 30
    if ((Test-Path $tmp) -and ((Get-Item $tmp).Length -gt 0)) { break }
  } catch {}
}
if (-not (Test-Path $tmp)) { exit 1 }

# 3) validate before installing (never let a broken/error payload overwrite prod)
$len  = (Get-Item $tmp).Length
$head = (Get-Content $tmp -TotalCount 5) -join ' '
if ($len -lt 50000 -or $head -notmatch '<html') { exit 1 }

Copy-Item $tmp (Join-Path $dir 'index.html') -Force
Set-Content -Path $shaFile -Value $new -Encoding ASCII
"$(Get-Date -Format 's') updated -> $new ($len bytes)" | Out-File $logFile -Append -Encoding ascii
