# ============================================================
#  cf_deploy.ps1 - verrou de deploiement CardForge
#
#  Le backend du :8765 NE LIT PAS le depot : il sert l'application installee
#  dans %LOCALAPPDATA%\DeepotusVideoGen. Toute edition doit donc y etre copiee.
#    - le JS/CSS du lab est servi en no-cache depuis le disque : une copie suffit ;
#    - un .py du backend exige une RELANCE du python qui tient le :8765.
#
#  Huit agents travaillent EN MEME TEMPS sur ce lab. Deux relances simultanees
#  se tuent mutuellement (l'un tue le python que l'autre vient de demarrer, puis
#  les deux echouent a lier le port). Ce script serialise les relances derriere
#  un verrou exclusif sur fichier.
#
#  Usage :
#    .\cf_deploy.ps1              deploie le lab (frontend\cardforge). Pas de
#                                 relance, pas de verrou. Rapide.
#    .\cf_deploy.ps1 -Backend     prend le verrou exclusif, deploie
#                                 backend\app\services\cards + backend\tests,
#                                 relance le python du :8765, attend
#                                 /api/health 200, relache le verrou (finally).
#    .\cf_deploy.ps1 -Check       compare depot et app fichier par fichier,
#                                 liste les ecarts, n'ecrit rien.
#
#  Contraintes du depot respectees ici :
#    - ASCII pur, UTF-8 SANS BOM (PowerShell 5.1 lit un fichier sans BOM en ANSI :
#      le moindre caractere accentue serait corrompu a l'execution) ;
#    - PowerShell 5.1 : pas de && , pas d'operateur ternaire, pas de ?? ;
#    - aucun tiret cadratin dans les chaines ;
#    - relance via Start-Process -WindowStyle Hidden, SANS redirection de flux :
#      rediriger les flux du python casse les ffmpeg qu'il lance (0xC0000142).
# ============================================================
[CmdletBinding()]
param(
    [switch]$Backend,
    [switch]$Check,
    [string]$AppRoot = "",
    [int]$Port = 8765,
    [int]$TimeoutSec = 180,
    [int]$StaleSec = 120
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$Repo = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $AppRoot) { $AppRoot = Join-Path $env:LOCALAPPDATA "DeepotusVideoGen" }
$HealthUrl = "http://127.0.0.1:$Port/api/health"
$LockPath  = Join-Path $AppRoot "cf_deploy.lock"

# Ce qui part du depot vers l'app. Cle = chemin relatif, identique des deux cotes.
$LAB_SETS     = @("frontend\cardforge")
$BACKEND_SETS = @("backend\app\services\cards", "backend\tests")

function Say {
    param([string]$Message)
    Write-Host ((Get-Date).ToString("HH:mm:ss.fff") + " [pid " + $PID + "] " + $Message)
}

# ---------------------------------------------------------------- copie / diff

function Get-TreeFiles {
    param([string]$Root)
    if (-not (Test-Path $Root)) { return @() }
    $prefix = (Resolve-Path $Root).Path.TrimEnd("\") + "\"
    $out = New-Object System.Collections.Generic.List[string]
    foreach ($f in (Get-ChildItem -Path $Root -Recurse -File -Force)) {
        if ($f.FullName -like "*\__pycache__\*") { continue }
        if ($f.Extension -eq ".pyc") { continue }
        $out.Add($f.FullName.Substring($prefix.Length))
    }
    return $out
}

function Get-Sha {
    param([string]$Path)
    return (Get-FileHash -Path $Path -Algorithm SHA256).Hash
}

# Copie depot -> app, fichier par fichier, seulement ce qui differe.
# Ne supprime jamais cote app : un fichier propre a l'app (venv, cache, artefact
# d'une autre piece) ne doit pas disparaitre parce qu'il est absent du depot.
function Sync-Set {
    param([string]$Rel)
    $src = Join-Path $Repo $Rel
    $dst = Join-Path $AppRoot $Rel
    if (-not (Test-Path $src)) {
        Say ("  SAUTE  " + $Rel + " (absent du depot)")
        return 0
    }
    if (-not (Test-Path $dst)) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }
    $n = 0
    # NB : surtout pas $rel comme variable de boucle. Les noms de variables sont
    # INSENSIBLES A LA CASSE en PowerShell : $rel ecraserait le parametre $Rel.
    foreach ($item in (Get-TreeFiles $src)) {
        $s = Join-Path $src $item
        $d = Join-Path $dst $item
        $need = $true
        if (Test-Path $d) {
            if ((Get-Sha $s) -eq (Get-Sha $d)) { $need = $false }
        }
        if ($need) {
            $parent = Split-Path -Parent $d
            if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
            Copy-Item -Path $s -Destination $d -Force
            $n = $n + 1
        }
    }
    Say ("  OK     " + $Rel + " : " + $n + " fichier(s) copie(s)")
    return $n
}

# Compare sans rien ecrire. Retourne la liste des ecarts.
function Compare-Set {
    param([string]$Rel)
    $src = Join-Path $Repo $Rel
    $dst = Join-Path $AppRoot $Rel
    $gaps = New-Object System.Collections.Generic.List[string]
    if (-not (Test-Path $src)) {
        $gaps.Add("ABSENT-DEPOT  " + $Rel)
        return $gaps
    }
    $srcFiles = Get-TreeFiles $src
    $dstFiles = Get-TreeFiles $dst
    # Idem : $item, pas $rel, sinon le parametre $Rel est ecrase des le 1er tour.
    foreach ($item in $srcFiles) {
        $s = Join-Path $src $item
        $d = Join-Path $dst $item
        if (-not (Test-Path $d)) {
            $gaps.Add("MANQUE-APP    " + $Rel + "\" + $item)
        } else {
            if ((Get-Sha $s) -ne (Get-Sha $d)) {
                $gaps.Add("DIFFERE       " + $Rel + "\" + $item)
            }
        }
    }
    foreach ($item in $dstFiles) {
        if ($srcFiles -notcontains $item) {
            $gaps.Add("EN-TROP-APP   " + $Rel + "\" + $item)
        }
    }
    return $gaps
}

# ---------------------------------------------------------------- verrou

function Read-Lock {
    param([string]$Path)
    try {
        $raw = [System.IO.File]::ReadAllText($Path)
    } catch {
        return $null
    }
    $lockPid = 0
    $ts = $null
    foreach ($line in ($raw -split "`r?`n")) {
        if ($line -match "^pid=(\d+)$")  { $lockPid = [int]$Matches[1] }
        if ($line -match "^ts=(.+)$")    {
            try { $ts = [datetime]::Parse($Matches[1], $null, [System.Globalization.DateTimeStyles]::RoundtripKind) } catch { $ts = $null }
        }
    }
    if ($lockPid -eq 0) { return $null }
    return [pscustomobject]@{ Pid = $lockPid; Ts = $ts; Raw = $raw }
}

function Test-PidAlive {
    param([int]$ProcId)
    $p = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
    return ($null -ne $p)
}

# Creation ATOMIQUE : FileMode CreateNew echoue si le fichier existe deja, et
# c'est le systeme de fichiers qui arbitre. Deux agents ne peuvent pas gagner.
# Le handle est referme aussitot pour que les autres puissent LIRE le pid et
# l'horodatage (diagnostic et reprise de verrou perime).
function Lock-Acquire {
    param([string]$Path, [int]$TimeoutSec, [int]$StaleSec)
    $dir = Split-Path -Parent $Path
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    $delayMs = 200
    $announced = $false
    while ($true) {
        $fs = $null
        try {
            $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
            $txt = "pid=" + $PID + "`r`nts=" + (Get-Date).ToUniversalTime().ToString("o") + "`r`n"
            $bytes = [System.Text.Encoding]::ASCII.GetBytes($txt)
            $fs.Write($bytes, 0, $bytes.Length)
            $fs.Flush()
            $fs.Close()
            if ($announced) {
                Say ("verrou PRIS apres " + [math]::Round($sw.Elapsed.TotalSeconds, 1) + " s d'attente")
            } else {
                Say "verrou PRIS immediatement (libre)"
            }
            return
        } catch {
            if ($null -ne $fs) { try { $fs.Close() } catch { } }
        }

        $info = Read-Lock $Path
        if ($null -eq $info) {
            # Verrou disparu (ou pas encore ecrit) entre nos deux instructions :
            # on retente tout de suite, la course est arbitree par CreateNew.
            Start-Sleep -Milliseconds 60
            continue
        }

        $ageSec = -1
        if ($null -ne $info.Ts) { $ageSec = [math]::Round(((Get-Date).ToUniversalTime() - $info.Ts).TotalSeconds, 1) }
        $alive = Test-PidAlive $info.Pid
        $stale = $false
        $why = ""
        if (-not $alive) { $stale = $true; $why = "detenteur pid " + $info.Pid + " mort" }
        if ($ageSec -gt $StaleSec) { $stale = $true; $why = "verrou perime (" + $ageSec + " s > " + $StaleSec + " s)" }

        if ($stale) {
            # Relecture avant suppression : si le contenu a change, quelqu'un a
            # deja repris le verrou et il ne faut surtout pas jeter le sien.
            $again = Read-Lock $Path
            if ($null -ne $again -and $again.Raw -eq $info.Raw) {
                Say ("REPRISE du verrou : " + $why)
                Remove-Item -Path $Path -Force -ErrorAction SilentlyContinue
            }
            Start-Sleep -Milliseconds (60 + (Get-Random -Minimum 0 -Maximum 120))
            continue
        }

        if (-not $announced) {
            Say ("verrou OCCUPE par pid " + $info.Pid + " (age " + $ageSec + " s) - attente de mon tour...")
            $announced = $true
        }

        if ($sw.Elapsed.TotalSeconds -ge $TimeoutSec) {
            throw ("Verrou toujours tenu par le pid " + $info.Pid + " apres " + $TimeoutSec + " s. Abandon.")
        }

        Start-Sleep -Milliseconds ($delayMs + (Get-Random -Minimum 0 -Maximum 150))
        # Recul progressif : bref au debut (le cas courant est une attente de
        # quelques secondes), puis plafonne pour ne pas marteler le disque.
        $delayMs = [math]::Min([int]($delayMs * 1.6), 3000)
    }
}

function Lock-Release {
    param([string]$Path)
    $info = Read-Lock $Path
    if ($null -eq $info) {
        Say "verrou deja absent au moment de rendre la main"
        return
    }
    if ($info.Pid -ne $PID) {
        Say ("verrou NON relache : il appartient maintenant au pid " + $info.Pid)
        return
    }
    Remove-Item -Path $Path -Force -ErrorAction SilentlyContinue
    Say "verrou RELACHE"
}

# ---------------------------------------------------------------- backend

function Test-Health {
    try {
        $r = Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 4
        return ($r.StatusCode -eq 200)
    } catch {
        return $false
    }
}

function Get-PortOwner {
    param([int]$P)
    $conn = Get-NetTCPConnection -LocalPort $P -State Listen -ErrorAction SilentlyContinue
    if (-not $conn) { return $null }
    foreach ($c in $conn) {
        $proc = Get-Process -Id $c.OwningProcess -ErrorAction SilentlyContinue
        if ($proc) { return $proc }
    }
    return $null
}

function Resolve-Python {
    $cands = @(
        (Join-Path $AppRoot "runtime\python\python.exe"),
        (Join-Path $AppRoot "backend\.venv\Scripts\python.exe")
    )
    foreach ($c in $cands) {
        if (Test-Path $c) { return $c }
    }
    throw ("Aucun python trouve dans " + $AppRoot + " (runtime\python ni backend\.venv).")
}

function Restart-Backend {
    $py = Resolve-Python
    $backendDir = Join-Path $AppRoot "backend"

    $owner = Get-PortOwner $Port
    if ($owner) {
        if ($owner.ProcessName -like "python*") {
            Say ("arret du python du :" + $Port + " (pid " + $owner.Id + ")")
            Stop-Process -Id $owner.Id -Force
        } else {
            throw ("Le port " + $Port + " est tenu par " + $owner.ProcessName + " (pid " + $owner.Id + "), pas par python. Refus de tuer.")
        }
    } else {
        Say ("rien n'ecoute sur le :" + $Port + ", demarrage a froid")
    }

    $freed = $false
    for ($i = 0; $i -lt 60; $i++) {
        if (-not (Get-PortOwner $Port)) { $freed = $true; break }
        Start-Sleep -Milliseconds 250
    }
    if (-not $freed) { throw ("Le port " + $Port + " n'a pas ete libere en 15 s.") }

    # ffmpeg/ffprobe embarques : le python les resout par le PATH herite.
    $binDir = Join-Path $AppRoot "bin"
    if (Test-Path $binDir) {
        if (-not ($env:PATH.StartsWith($binDir))) { $env:PATH = $binDir + ";" + $env:PATH }
    }
    # Jamais de bytecode perime : un .py fraichement copie peut avoir une mtime
    # plus ancienne que le .pyc voisin, et python chargerait l'ANCIEN code.
    $env:PYTHONDONTWRITEBYTECODE = "1"

    Say "demarrage du python (Start-Process -WindowStyle Hidden, sans redirection de flux)"
    Start-Process -FilePath $py `
                  -ArgumentList @("-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "$Port") `
                  -WorkingDirectory $backendDir `
                  -WindowStyle Hidden

    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.Elapsed.TotalSeconds -lt 90) {
        if (Test-Health) {
            Say ("/api/health 200 apres " + [math]::Round($sw.Elapsed.TotalSeconds, 1) + " s")
            return
        }
        Start-Sleep -Milliseconds 400
    }
    throw "Le backend n'a pas repondu 200 sur /api/health en 90 s."
}

# ---------------------------------------------------------------- modes

Say ("depot : " + $Repo)
Say ("app   : " + $AppRoot)

if ($Check) {
    Say "mode -Check : comparaison depot / app, aucune ecriture"
    $all = New-Object System.Collections.Generic.List[string]
    foreach ($s in ($LAB_SETS + $BACKEND_SETS)) {
        foreach ($g in (Compare-Set $s)) { $all.Add($g) }
    }
    if ($all.Count -eq 0) {
        Write-Host ""
        Write-Host "0 ecart : le depot et l'app sont identiques." -ForegroundColor Green
        exit 0
    }
    Write-Host ""
    Write-Host ($all.Count.ToString() + " ecart(s) :") -ForegroundColor Yellow
    foreach ($g in $all) { Write-Host ("  " + $g) }
    exit 1
}

if (-not $Backend) {
    Say "mode lab : deploiement du frontend, sans relance ni verrou"
    $total = 0
    foreach ($s in $LAB_SETS) { $total = $total + (Sync-Set $s) }
    Say ("termine : " + $total + " fichier(s) mis a jour. Le lab est servi en no-cache, recharge la page.")
    exit 0
}

Say "mode -Backend : verrou exclusif requis (relance du python partagee entre 8 agents)"
Lock-Acquire -Path $LockPath -TimeoutSec $TimeoutSec -StaleSec $StaleSec
try {
    $total = 0
    foreach ($s in ($LAB_SETS + $BACKEND_SETS)) { $total = $total + (Sync-Set $s) }
    Say ("deploiement : " + $total + " fichier(s) mis a jour")
    Restart-Backend
    Say "OK : backend relance et vivant"
} finally {
    # Le verrou tombe MEME si le deploiement ou la relance a echoue : sinon les
    # sept autres agents attendraient 120 s la peremption pour rien.
    Lock-Release -Path $LockPath
}
exit 0
