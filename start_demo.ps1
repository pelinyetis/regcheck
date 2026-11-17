<#
.SYNOPSIS
  RegCheck demo: starts mevzuat-mcp + yargi-mcp over streamable HTTP (with a bearer
  token) and opens a Cloudflare quick tunnel for each. Prints the public MCP URLs.

.USAGE
  powershell -ExecutionPolicy Bypass -File .\start_demo.ps1          # start everything
  powershell -ExecutionPolicy Bypass -File .\start_demo.ps1 -Stop    # stop everything
  powershell -ExecutionPolicy Bypass -File .\start_demo.ps1 -NoTunnel  # local only

  Quick-tunnel URLs are random and CHANGE on every start; re-enter them in UiPath.
#>
param(
    [switch]$Stop,
    [switch]$NoTunnel,
    [int]$MevzuatPort = 8101,
    [int]$YargiPort = 8102
)
$ErrorActionPreference = 'Stop'
$Root    = $PSScriptRoot
$LogDir  = Join-Path $Root 'remote\logs'
$PidFile = Join-Path $LogDir 'pids.json'
$TokFile = Join-Path $Root 'secrets\mcp_token.txt'
New-Item -ItemType Directory -Force $LogDir | Out-Null

function Stop-Demo([switch]$Quiet) {
    if (Test-Path $PidFile) {
        foreach ($procId in (Get-Content $PidFile -Raw | ConvertFrom-Json)) {
            # kill the whole tree (uvx -> python, cloudflared)
            & taskkill.exe /PID $procId /T /F 2>$null | Out-Null
        }
        Remove-Item $PidFile -Force
    }
    # belt and braces: free the ports
    foreach ($port in @($MevzuatPort, $YargiPort)) {
        $c = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        foreach ($x in $c) { & taskkill.exe /PID $x.OwningProcess /T /F 2>$null | Out-Null }
    }
    if (-not $Quiet) { Write-Host 'RegCheck demo stopped.' }
}

if ($Stop) { Stop-Demo; return }
Stop-Demo -Quiet   # clean restart

# --- prerequisites -----------------------------------------------------------
if (-not (Get-Command uvx -ErrorAction SilentlyContinue)) { throw 'uvx not found. Install uv first: https://docs.astral.sh/uv/' }
$Cloudflared = Join-Path $Root 'tools\bin\cloudflared.exe'     # portable copy (no admin needed)
if (-not (Test-Path $Cloudflared)) { $Cloudflared = (Get-Command cloudflared -ErrorAction SilentlyContinue).Source }
if (-not $Cloudflared) {
    foreach ($p in @("$env:ProgramFiles\cloudflared\cloudflared.exe", "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe", "$env:LOCALAPPDATA\Microsoft\WinGet\Links\cloudflared.exe")) {
        if (Test-Path $p) { $Cloudflared = $p; break }
    }
}
if (-not $NoTunnel -and -not $Cloudflared) { throw 'cloudflared not found. Put cloudflared-windows-amd64.exe at tools\bin\cloudflared.exe (see mcp_setup.md) or: winget install --id Cloudflare.cloudflared -e' }

# --- bearer token --------------------------------------------------------------
if (-not (Test-Path $TokFile)) {
    New-Item -ItemType Directory -Force (Split-Path $TokFile) | Out-Null
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    $tok = [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
    [IO.File]::WriteAllText($TokFile, $tok)
}
$Token = (Get-Content $TokFile -Raw).Trim()
$env:MCP_BEARER_TOKEN = $Token
$env:PYTHONUTF8 = '1'

# --- MCP servers ---------------------------------------------------------------
$Serve = Join-Path $Root 'remote\serve_http.py'
$servers = @(
    @{ Name = 'mevzuat'; Port = $MevzuatPort; Args = @('-q', '--from', 'mevzuat-mcp@0.3.0', '--with', 'uvicorn', 'python', '-I', $Serve, 'mevzuat_mcp_server', $MevzuatPort) },
    @{ Name = 'yargi';   Port = $YargiPort;   Args = @('-q', '--with', 'mcp<2', '--from', 'yargi-mcp@0.2.2', '--with', 'uvicorn', 'python', '-I', $Serve, 'mcp_server_main', $YargiPort) }
)
$pids = @()
foreach ($s in $servers) {
    $quoted = $s.Args | ForEach-Object { if ("$_" -match '[\s<>]') { '"' + $_ + '"' } else { "$_" } }
    $p = Start-Process -FilePath 'uvx' -ArgumentList $quoted -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $LogDir "$($s.Name).out.log") `
        -RedirectStandardError  (Join-Path $LogDir "$($s.Name).log")
    $pids += $p.Id
}
ConvertTo-Json @($pids) | Set-Content $PidFile

foreach ($s in $servers) {
    $ok = $false
    for ($i = 0; $i -lt 90 -and -not $ok; $i++) {
        try { $ok = (Invoke-WebRequest "http://127.0.0.1:$($s.Port)/healthz" -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $ok) { throw "$($s.Name) did not start; see $LogDir\$($s.Name).log" }
    Write-Host "[ok] $($s.Name) listening on http://127.0.0.1:$($s.Port)/mcp"
}

# --- tunnels ---------------------------------------------------------------------
$urls = @{}
if (-not $NoTunnel) {
    foreach ($s in $servers) {
        $log = Join-Path $LogDir "tunnel-$($s.Name).log"
        if (Test-Path $log) { Remove-Item $log -Force }
        $p = Start-Process -FilePath $Cloudflared -WindowStyle Hidden -PassThru `
            -ArgumentList @('tunnel', '--no-autoupdate', '--url', "http://127.0.0.1:$($s.Port)", '--logfile', "`"$log`"")
        $pids += $p.Id
        ConvertTo-Json @($pids) | Set-Content $PidFile
        $url = $null
        for ($i = 0; $i -lt 60 -and -not $url; $i++) {
            Start-Sleep -Seconds 1
            if (Test-Path $log) {
                $m = Select-String -Path $log -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -AllMatches | Select-Object -First 1
                if ($m) { $url = $m.Matches[0].Value }
            }
        }
        if (-not $url) { throw "tunnel for $($s.Name) did not come up; see $log" }
        $urls[$s.Name] = "$url/mcp"
    }
    # wait until the public hostnames resolve and answer
    foreach ($n in $urls.Keys) {
        $h = $urls[$n] -replace '/mcp$', '/healthz'
        for ($i = 0; $i -lt 45; $i++) {
            try { if ((Invoke-WebRequest $h -UseBasicParsing -TimeoutSec 5).StatusCode -eq 200) { break } } catch { Start-Sleep -Seconds 2 }
        }
    }
}

$info = [ordered]@{
    started     = (Get-Date).ToString('s')
    mevzuat_url = if ($urls['mevzuat']) { $urls['mevzuat'] } else { "http://127.0.0.1:$MevzuatPort/mcp" }
    yargi_url   = if ($urls['yargi'])   { $urls['yargi'] }   else { "http://127.0.0.1:$YargiPort/mcp" }
    auth_header = 'Authorization: Bearer <token in secrets\mcp_token.txt>'
}
$info | ConvertTo-Json | Set-Content (Join-Path $LogDir 'urls.json')

Write-Host ''
Write-Host '================ RegCheck MCP servers ================' -ForegroundColor Cyan
Write-Host "mevzuat-mcp : $($info.mevzuat_url)"
Write-Host "yargi-mcp   : $($info.yargi_url)"
Write-Host "Header      : Authorization: Bearer $Token"
Write-Host '======================================================' -ForegroundColor Cyan
Write-Host "Stop with: .\start_demo.ps1 -Stop    (logs: $LogDir)"
