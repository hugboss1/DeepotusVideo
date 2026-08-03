# Sonde POST-DEPLOIEMENT obligatoire (incident overlay MSIX 14/06-20/07/2026).
# A lancer apres chaque redeploiement/relance de l'app pour prouver que le
# backend ecrit bien dans le monde reel :
#   1. GET /api/health -> fs_virtualized doit etre false (garde interne) ;
#   2. upload d'un PNG sonde -> il doit apparaitre dans GET /api/images
#      (un backend conteneurise ecrit dans l'overlay : la sonde disparait
#      du listing) ; la sonde est ensuite supprimee.
# Sort avec code 1 si l'un des deux checks echoue. Utilisable depuis
# n'importe quel shell (la sonde passe par l'API, pas par le filesystem).
# NB : fichier volontairement ASCII pur (PowerShell 5.1 lit sans BOM en ANSI).
$api = "http://127.0.0.1:8765/api"
$fail = $false

try {
  $h = (Invoke-WebRequest -UseBasicParsing "$api/health" -TimeoutSec 10).Content | ConvertFrom-Json
} catch {
  Write-Host "[FAIL] backend injoignable: $($_.Exception.Message)"; exit 1
}
if ($h.fs_virtualized -eq $false) {
  Write-Host "[OK ] health.fs_virtualized = false"
} else {
  Write-Host "[FAIL] health.fs_virtualized = $($h.fs_virtualized) - backend conteneurise ou garde absent !"
  $fail = $true
}

Add-Type -AssemblyName System.Drawing
$bmp = New-Object System.Drawing.Bitmap(2, 2)
$tmp = Join-Path $env:TEMP "dz_probe.png"
$bmp.Save($tmp, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$name = "probe_postdeploy_$(Get-Date -Format 'HHmmss').png"
$curl = "$env:SystemRoot\System32\curl.exe"
& $curl -s -X POST "$api/images/upload" -F "file=@$tmp;filename=$name" | Out-Null
Start-Sleep -Milliseconds 400
$lst = (Invoke-WebRequest -UseBasicParsing "$api/images" -TimeoutSec 10).Content | ConvertFrom-Json
$seen = ($lst.images | Where-Object filename -eq $name) -ne $null
& $curl -s -X DELETE "$api/images/$name" | Out-Null
if ($seen) {
  Write-Host "[OK ] sonde upload visible dans le listing (ecritures reelles)"
} else {
  Write-Host "[FAIL] sonde upload INVISIBLE du listing - ecritures deviees vers l'overlay !"
  $fail = $true
}

if ($fail) { exit 1 }
Write-Host "postdeploy probe: 2/2 OK"
