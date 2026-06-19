# Stop Deepotus Video Gen cleanly (kills the hidden uvicorn process).
$conn = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($conn) {
    $owner = Get-Process -Id $conn.OwningProcess -ErrorAction SilentlyContinue
    if ($owner -and $owner.ProcessName -like "python*") {
        Stop-Process -Id $owner.Id -Force
        Write-Host "Deepotus Video Gen stopped (PID $($owner.Id))." -ForegroundColor Green
        exit 0
    }
}
Write-Host "Nothing listening on port 8765 - already stopped." -ForegroundColor Yellow
