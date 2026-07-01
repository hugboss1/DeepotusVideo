<#
  Claude Code - IMPORT sessions & chats (run on the NEW PC).
  Merges the exported Claude Code home into ~\.claude on this PC.

  Usage:
    powershell -ExecutionPolicy Bypass -File .\import-claude-sessions.ps1 -Src "E:\deepotus-transfer"
#>
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$Src)
$ErrorActionPreference = "Stop"
$in = Join-Path $Src "claude-home"
if (-not (Test-Path $in)) { throw "Source not found: $in (run export-claude-sessions.ps1 first)" }
$home_ = Join-Path $env:USERPROFILE ".claude"
New-Item -ItemType Directory -Force -Path $home_ | Out-Null

Write-Host "Merging Claude Code sessions/chats/memory into $home_ ..."
# /E merges (does not delete existing); your current .claude is preserved + augmented
robocopy $in $home_ /E /R:1 /W:1 /NFL /NDL /NJH /NP | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed, code $LASTEXITCODE" }

Write-Host "DONE. Your chats & memory are restored." -ForegroundColor Green
Write-Host "To resume a chat: open Claude Code in the SAME project folder path as on the source PC," -ForegroundColor Yellow
Write-Host "then 'claude --resume' (or /resume). Transcripts are also readable as .jsonl under ~\.claude\projects." -ForegroundColor Yellow
