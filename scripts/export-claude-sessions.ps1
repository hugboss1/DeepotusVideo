<#
  Claude Code - EXPORT sessions & chats (run on THIS PC).
  Copies your Claude Code home (~\.claude): all project transcripts (.jsonl),
  memory, command history, settings, skills & plugins. Skips transient caches.

  Usage:
    powershell -ExecutionPolicy Bypass -File .\export-claude-sessions.ps1 -Dest "E:\deepotus-transfer"
#>
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$Dest)
$ErrorActionPreference = "Stop"
$home_ = Join-Path $env:USERPROFILE ".claude"
if (-not (Test-Path $home_)) { throw "Claude home not found: $home_" }
$out = Join-Path $Dest "claude-home"

# skip transient / machine-specific dirs (re-created automatically)
$xd = @("cache", "chrome", "ide", "shell-snapshots", "downloads", "session-env", "debug")
$xdArgs = @()
foreach ($d in $xd) { $xdArgs += @("/XD", (Join-Path $home_ $d)) }

Write-Host "Copying Claude Code sessions, chats, memory, settings, skills..."
$args = @($home_, $out, "/E", "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NP") + $xdArgs
robocopy @args | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed, code $LASTEXITCODE" }

"source_user=$env:USERNAME" | Set-Content (Join-Path $out "_claude-info.txt") -Encoding UTF8
$mb = [math]::Round(((Get-ChildItem $out -Recurse -File -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum) / 1MB, 0)
Write-Host "DONE -> $out  ($mb MB). Run import-claude-sessions.ps1 on the other PC." -ForegroundColor Green
Write-Host "NOTE: to RESUME a chat there, open the project at the SAME folder path (same Windows user)." -ForegroundColor Yellow
