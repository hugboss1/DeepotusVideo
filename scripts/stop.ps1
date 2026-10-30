# Stop Deepotus Video Gen cleanly (kills the hidden uvicorn backend and its children).
#
# t377 (30/10/2026) : le backend est reconnu par sa LIGNE DE COMMANDE, plus seulement par le PID qui écoute.
# Constat du 30/10 : netstat montrait 127.0.0.1:8765 LISTENING 0 (PID 0) alors qu'un backend installé tournait ;
# l'ancienne version, qui ne regardait que ce PID, n'arrêtait rien et l'ancien code restait servi. Le 10/10 déjà,
# un enfant spawn_main(parent_pid=…) gardait le socket d'un parent tué.
#   1. racines : `-m uvicorn app.main:app … --port <Port>` dont l'exécutable est SOUS le dossier de l'app,
#      plus le processus qui écoute le port si son exécutable est sous ce dossier ;
#   2. descendants : ParentProcessId ou `spawn_main(parent_pid=<pid>` d'un processus retenu, nés après lui
#      (venv : le vrai python est l'enfant du lanceur .venv\Scripts\python.exe) ;
#   3. on les arrête, puis on attend que le port ne réponde PLUS en HTTP (pas netstat).
# Un processus d'une autre application (exécutable hors du dossier) n'est jamais touché.
# Sortie : 0 = le port ne répond plus ; 2 = il répond encore (autre programme, ou arrêt impossible).
param(
    [int]$Port = 8765,
    [string]$AppDir = (Split-Path -Parent $PSScriptRoot),
    [int]$DelaiSec = 15
)

$racine = [IO.Path]::GetFullPath($AppDir).TrimEnd('\') + '\'

function Sous-App($p) {
    return $p -and $p.ExecutablePath -and $p.ExecutablePath.StartsWith($racine, [StringComparison]::OrdinalIgnoreCase)
}

function Port-Repond {
    try {
        $req = [Net.WebRequest]::Create("http://127.0.0.1:$Port/api/health")
        $req.Proxy = $null
        $req.Timeout = 1500
        $rep = $req.GetResponse()
        $rep.Close()
        return $true
    } catch [Net.WebException] {
        # une réponse HTTP d'erreur (404, 500…) : quelque chose sert encore le port
        return $null -ne $_.Exception.Response
    } catch {
        return $false
    }
}

$tous = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue)
$motifPort = "--port[\s=]+$Port(\s|`"|$)"
$retenus = @{}
foreach ($p in $tous) {
    if ((Sous-App $p) -and $p.CommandLine -match '-m\s+uvicorn\s+app\.main:app\b' -and $p.CommandLine -match $motifPort) {
        $retenus[[int]$p.ProcessId] = $p
    }
}
foreach ($c in @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)) {
    $p = $tous | Where-Object { $_.ProcessId -eq $c.OwningProcess -and $_.ProcessId -ne 0 } | Select-Object -First 1
    if (Sous-App $p) { $retenus[[int]$p.ProcessId] = $p }
}
do {
    $ajout = $false
    foreach ($p in $tous) {
        $id = [int]$p.ProcessId
        if ($retenus.ContainsKey($id) -or $id -eq 0) { continue }
        $parent = [int]$p.ParentProcessId
        if ($p.CommandLine -match 'spawn_main\(parent_pid=(\d+)') { $parent = [int]$Matches[1] }
        # un PID se réutilise : le descendant doit être né APRÈS le processus retenu
        if ($retenus.ContainsKey($parent) -and $p.CreationDate -ge $retenus[$parent].CreationDate) {
            $retenus[$id] = $p
            $ajout = $true
        }
    }
} while ($ajout)

foreach ($id in $retenus.Keys) {
    Stop-Process -Id $id -Force -ErrorAction SilentlyContinue
}
if ($retenus.Count) {
    Write-Host "Deepotus Video Gen stopped (PID $(@($retenus.Keys | Sort-Object) -join ', '))." -ForegroundColor Green
}

$fin = (Get-Date).AddSeconds($DelaiSec)
while (Port-Repond) {
    if ((Get-Date) -gt $fin) {
        Write-Host "Port $Port still answers: it is held by another program, or a process could not be stopped." -ForegroundColor Red
        exit 2
    }
    Start-Sleep -Milliseconds 250
}
if (-not $retenus.Count) {
    Write-Host "Nothing running on port $Port - already stopped." -ForegroundColor Yellow
}
exit 0
