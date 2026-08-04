# Sonde READ-ONLY de l'etat REEL de DeepotusVideoGenData, a executer HORS
# du conteneur MSIX de Claude (via explorer.exe ou schtasks) — car tout shell
# lance depuis une session Claude voit l'overlay LocalCache a la place des
# vrais fichiers. Ecrit son rapport dans %USERPROFILE%\dz_desandbox_report.txt.
$out = "$env:USERPROFILE\dz_desandbox_report.txt"
$root = "$env:LOCALAPPDATA\DeepotusVideoGenData"
$lines = @()
$lines += "PROBE_START $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$lines += "whoami: $env:USERNAME  pid: $PID"
$lines += "--- racine ---"
Get-ChildItem $root -File -ErrorAction SilentlyContinue | ForEach-Object {
  $lines += ("{0}  {1,10} o  {2}" -f $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), $_.Length, $_.Name)
}
$lines += "--- comptes assets ---"
foreach ($d in @("assets\images", "assets\outputs\final", "assets\outputs\videos", "assets\outputs\sprites", "assets\news")) {
  $p = Join-Path $root $d
  $n = (Get-ChildItem $p -File -Recurse -ErrorAction SilentlyContinue | Measure-Object).Count
  $lines += "$d : $n fichiers"
}
$lines += "--- 8 plus recents assets\images ---"
Get-ChildItem "$root\assets\images" -File -ErrorAction SilentlyContinue |
  Sort-Object LastWriteTime -Descending | Select-Object -First 8 | ForEach-Object {
    $lines += ("{0}  {1}" -f $_.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"), $_.Name)
  }
$lines += "PROBE_END"
[System.IO.File]::WriteAllLines($out, $lines)
