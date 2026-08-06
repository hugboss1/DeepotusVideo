# Run the backend test suite — ONE PROCESS PER FILE.
#
# The suite is 31 self-running scripts, not a shared-process pytest suite:
# most files do their work at import time (module-level asyncio.run) and
# freeze app.config / the DB singletons with their own temp environment. Run
# them together and the first module's settings leak into every later one, so
# `pytest tests` can never be green no matter how healthy the code is. One
# process per file is the harness they were written for.
#
#   .\scripts\run-tests.ps1                 # full suite
#   .\scripts\run-tests.ps1 -Filter meshy   # only files matching *meshy*
#   .\scripts\run-tests.ps1 -Python C:\path\to\python.exe
[CmdletBinding()]
param(
    [string]$Filter = "",
    [string]$Python = ""
)

$ErrorActionPreference = "Continue"   # a failing test file must not abort the run
$repo = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repo "backend"
$testsDir = Join-Path $backend "tests"

if (-not $Python) {
    # Prefer the app's embedded runtime (same interpreter the product ships),
    # fall back to whatever python is on PATH.
    $embedded = Join-Path $repo "runtime\python\python.exe"
    if (Test-Path $embedded) { $Python = $embedded }
    else {
        $onPath = Get-Command python -ErrorAction SilentlyContinue
        if (-not $onPath) { throw "No python found. Pass -Python <path>." }
        $Python = $onPath.Source
    }
}
Write-Host "python : $Python"
Write-Host "tests  : $testsDir`n"

$files = Get-ChildItem -Path $testsDir -Filter "test_*.py" | Sort-Object Name
if ($Filter) { $files = $files | Where-Object { $_.Name -like "*$Filter*" } }
if (-not $files) { throw "No test files matched '$Filter'." }

$passed = New-Object System.Collections.Generic.List[string]
$failed = New-Object System.Collections.Generic.List[string]
$sw = [Diagnostics.Stopwatch]::StartNew()

foreach ($f in $files) {
    # A file that invokes its tests at module level must run as a script:
    # under pytest the import runs them once and pytest runs them again, and
    # the second pass hits state the first one already created (that is the
    # UNIQUE-constraint failure in test_voice_providers). Everything else goes
    # through pytest, which supplies conftest's sys.path entry.
    # ...and a file with no collectable test function is a script by definition.
    $src = Get-Content $f.FullName -Raw
    $isScript = ($src -match '(?m)^(asyncio\.run\(|test_[A-Za-z0-9_]*\()') -or
                ($src -notmatch '(?m)^\s*(async )?def test_')

    Write-Host ("-> {0,-34}" -f $f.Name) -NoNewline
    # Redirect to a file rather than through the pipeline: in Windows
    # PowerShell, piping a native command's stderr wraps every line in a
    # NativeCommandError and reports failure even on exit code 0.
    $log = [IO.Path]::GetTempFileName()
    Push-Location $backend
    # Script mode bypasses conftest.py, so `import app` needs the path here.
    $env:PYTHONPATH = $backend
    try {
        if ($isScript) { & $Python $f.FullName > $log 2>&1 }
        else { & $Python -m pytest ("tests/" + $f.Name) -q > $log 2>&1 }
        $code = $LASTEXITCODE
        if (-not $isScript -and $code -eq 5) {   # pytest collected nothing
            & $Python $f.FullName > $log 2>&1
            $code = $LASTEXITCODE
        }
    } finally { Pop-Location }

    if ($code -eq 0) {
        $passed.Add($f.Name); Write-Host " PASS" -ForegroundColor Green
    } else {
        $failed.Add($f.Name); Write-Host " FAIL ($code)" -ForegroundColor Red
        Get-Content $log -Tail 12 | ForEach-Object { Write-Host "     $_" -ForegroundColor DarkGray }
    }
    Remove-Item $log -ErrorAction SilentlyContinue
}

$sw.Stop()
Write-Host ("`n{0} passed, {1} failed in {2:N0}s" -f $passed.Count, $failed.Count, $sw.Elapsed.TotalSeconds)
if ($failed.Count) {
    Write-Host "failed: $($failed -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "suite green" -ForegroundColor Green
