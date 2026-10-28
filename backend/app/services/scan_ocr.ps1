# t312 (28/10/2026) - pont Windows.Media.Ocr pour scan_ocr.py (Windows PowerShell 5.1, WinRT).
#   -Langues                       -> {"langues": ["en-US", "fr-FR", ...]}
#   -Image <png> -Langue fr-FR     -> {"langue", "angle", "lignes": [{"texte", "mots": [{"texte","x","y","l","h"}]}]}
# JSON UTF-8 sur stdout. Codes de sortie : 0 ok, 2 langue non installee, 1 toute autre erreur (message bref sur
# stderr, jamais le texte lu). Lance par scan_ocr.py : powershell -NoProfile -NonInteractive -ExecutionPolicy Bypass -File.
param(
    [string]$Image = "",
    [string]$Langue = "fr-FR",
    [switch]$Langues
)
$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding $false

function Sortir([int]$code, [string]$message) {
    [Console]::Error.WriteLine($message)
    exit $code
}

try {
    Add-Type -AssemblyName System.Runtime.WindowsRuntime
    $null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Globalization.Language, Windows.Foundation, ContentType = WindowsRuntime]
    $null = [Windows.Storage.Streams.IRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
    $null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics, ContentType = WindowsRuntime]
    $null = [Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics, ContentType = WindowsRuntime]
} catch {
    Sortir 1 "WinRT indisponible"
}

if ($Langues) {
    $liste = New-Object System.Collections.Generic.List[string]
    foreach ($l in [Windows.Media.Ocr.OcrEngine]::AvailableRecognizerLanguages) { $liste.Add([string]$l.LanguageTag) }
    [Console]::Out.Write((ConvertTo-Json -Compress -InputObject @{ langues = $liste.ToArray() }))
    exit 0
}

$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq "AsTask" -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq "IAsyncOperation``1"
} | Select-Object -First 1

function Attendre($operation, [Type]$type) {
    $tache = $asTask.MakeGenericMethod($type).Invoke($null, @($operation))
    $null = $tache.Wait(-1)
    $tache.Result
}

try {
    $langueWinRT = New-Object Windows.Globalization.Language $Langue
} catch {
    Sortir 2 "langue inconnue"
}
if (-not [Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($langueWinRT)) { Sortir 2 "langue non installee" }
$moteur = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($langueWinRT)
if ($null -eq $moteur) { Sortir 2 "langue non installee" }

try {
    # Flux .NET -> IRandomAccessStream : pas de StorageFile, qui refuse les chemins longs (> 260 caracteres).
    $netflux = [System.IO.File]::OpenRead($Image)
    $flux = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($netflux)
    try {
        $decodeur = Attendre ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($flux)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Attendre ($decodeur.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $resultat = Attendre ($moteur.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    } finally {
        $flux.Dispose()
        $netflux.Dispose()
    }
} catch {
    Sortir 1 "lecture impossible"
}

$lignes = New-Object System.Collections.Generic.List[object]
foreach ($ligne in $resultat.Lines) {
    $mots = New-Object System.Collections.Generic.List[object]
    foreach ($mot in $ligne.Words) {
        $r = $mot.BoundingRect
        $mots.Add(@{ texte = [string]$mot.Text; x = [double]$r.X; y = [double]$r.Y; l = [double]$r.Width; h = [double]$r.Height })
    }
    $lignes.Add(@{ texte = [string]$ligne.Text; mots = $mots.ToArray() })
}
$angle = $null
if ($null -ne $resultat.TextAngle) { $angle = [double]$resultat.TextAngle }
[Console]::Out.Write((ConvertTo-Json -Compress -Depth 6 -InputObject @{ langue = $Langue; angle = $angle; lignes = $lignes.ToArray() }))
exit 0
