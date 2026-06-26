' ============================================================
' DEEPOTUS VIDEO GEN -- Silent launcher (no console windows)
' Starts the backend hidden (it also serves the built frontend),
' waits for /api/health, then opens the default browser.
'
' Python resolution order:
'   1. <app>\runtime\python\python.exe   (installer build: embedded runtime)
'   2. <app>\backend\.venv\Scripts\python.exe (developer install)
' If <app>\bin exists (installer build ships ffmpeg there), it is
' prepended to PATH so ffmpeg/ffprobe resolve without a system install.
'
' Stop the app: scripts\stop.ps1 or kill python from Task Manager.
' ============================================================
Option Explicit

Dim fso, shell, appDir, py, url, attempts, binDir, env
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

appDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
url = "http://127.0.0.1:8765"

py = appDir & "\runtime\python\python.exe"
If Not fso.FileExists(py) Then py = appDir & "\backend\.venv\Scripts\python.exe"

If Not fso.FileExists(py) Then
  MsgBox "Python runtime not found:" & vbCrLf & py & vbCrLf & vbCrLf & _
         "Reinstall the application, or run scripts\install.ps1 for a developer setup.", _
         vbExclamation, "Deepotus Video Gen"
  WScript.Quit 1
End If

' A relaunch must ALWAYS run the CURRENT code + the latest backend\.env
' (saved API keys, channel creds). The old build short-circuited here when a
' backend was already healthy, so a stale process kept serving old code and
' saved settings never took effect until python was killed by hand. Instead,
' stop any existing backend on :8765 first, then start a fresh one below.
StopExistingBackend()

' Bundled ffmpeg (installer build): prepend <app>\bin to this process PATH —
' the spawned python inherits it.
Set env = shell.Environment("PROCESS")
binDir = appDir & "\bin"
If fso.FolderExists(binDir) Then
  env("PATH") = binDir & ";" & env("PATH")
End If
' Never run stale compiled bytecode: an upgrade can leave a __pycache__\*.pyc
' whose embedded source-mtime is >= the freshly-copied .py (Inno preserves the
' staged file's older timestamp), so Python would silently load OLD code and the
' app would look broken (e.g. "lost keys / empty library"). Forcing no-bytecode
' means every boot compiles from the real .py — bulletproof, ~0.5s cost.
env("PYTHONDONTWRITEBYTECODE") = "1"

' Start uvicorn hidden (window style 0), working dir = backend\
shell.CurrentDirectory = appDir & "\backend"
shell.Run """" & py & """ -m uvicorn app.main:app --host 127.0.0.1 --port 8765", 0, False

' Wait for the API (up to ~45 s; first boot creates the DB), then open the browser.
attempts = 0
Do While attempts < 90
  WScript.Sleep 500
  If HealthOk() Then
    shell.Run url, 1, False
    WScript.Quit 0
  End If
  attempts = attempts + 1
Loop

MsgBox "The app did not start within 45 seconds." & vbCrLf & _
       "Check backend\.env, or run scripts\launch.ps1 to see the error.", _
       vbExclamation, "Deepotus Video Gen"
WScript.Quit 1

Function HealthOk()
  HealthOk = False
  On Error Resume Next
  Dim req
  Set req = CreateObject("MSXML2.XMLHTTP")
  req.Open "GET", url & "/api/health", False
  req.Send
  If Err.Number = 0 And req.Status = 200 Then HealthOk = True
  On Error GoTo 0
End Function

' Stop a previously-launched backend so this run starts fresh. Fast no-op when
' nothing is listening. Reuses scripts\stop.ps1 (kills the python holding
' :8765), then waits for the port to free before the caller re-binds it.
Sub StopExistingBackend()
  On Error Resume Next
  If Not HealthOk() Then Exit Sub
  shell.Run "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & appDir & "\scripts\stop.ps1""", 0, True
  Dim tries
  tries = 0
  Do While HealthOk() And tries < 20
    WScript.Sleep 250
    tries = tries + 1
  Loop
  On Error GoTo 0
End Sub
