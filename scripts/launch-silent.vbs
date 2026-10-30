' ============================================================
' DEEPOTUS VIDEO GEN -- Silent launcher (no console windows)
' Starts the backend hidden (it also serves the built frontend),
' waits for /api/health (on 127.0.0.1), then opens the default browser on
' http://deepotus.localhost:8765 -- browsers resolve *.localhost to loopback
' without any hosts file (RFC 6761): the app has a NAME, not an IP.
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

Dim fso, shell, appDir, py, url, urlApp, attempts, binDir, env, hostArg, depart, vieux
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

appDir = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))
url = "http://127.0.0.1:8765"
urlApp = "http://deepotus.localhost:8765"

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
' t386 (30/10/2026) : l'arret reconnait le backend a sa LIGNE DE COMMANDE (stop.ps1), et le navigateur ne
' s'ouvre que si /api/health repond depuis le processus lance CI-DESSOUS (pid rendu par la sante, ne apres
' le lancement). Le 30/10, le socket du 8765 etait attribue au PID 0 : rien n'etait arrete, le nouveau
' uvicorn sortait sans bruit et l'ANCIEN code restait servi derriere une sante verte.
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
' L'hote d'ecoute vient du .env de l'utilisateur (DATA_ROOT), pas d'ici : le defaut reste 127.0.0.1, et
' HOST=0.0.0.0 ouvre le reseau local au compagnon mobile (plan mobile T5, tache #56, 01/10/2026). Sans cette
' lecture, changer config.py ne changerait RIEN sur une machine installee : c'est CETTE ligne qui decide.
hostArg = LireHote(DataRoot() & "\.env")
' 2 s de marge : CreationDate (WMI) est a la microseconde, Now a la seconde.
depart = DateAdd("s", -2, Now)
shell.Run """" & py & """ -m uvicorn app.main:app --host " & hostArg & " --port 8765", 0, False

' Wait for the API (up to ~45 s; first boot creates the DB), then open the browser -- only once the
' answer comes from the NEW process (t386).
attempts = 0
vieux = False
Do While attempts < 90
  WScript.Sleep 500
  If HealthOk() Then
    If ProcessusNeuf(SantePid(), depart) Then
      shell.Run urlApp, 1, False
      WScript.Quit 0
    End If
    vieux = True
  End If
  attempts = attempts + 1
Loop

If vieux Then
  MsgBox "An older backend still answers on port 8765: the new one could not start." & vbCrLf & _
         "Run scripts\stop.ps1, then start the app again.", _
         vbExclamation, "Deepotus Video Gen"
  WScript.Quit 1
End If

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

' pid du processus qui repond a /api/health (0 si aucun, ou un ancien backend sans ce champ). WinHTTP
' (ServerXMLHTTP) plutot que XMLHTTP : aucun cache WinINet ne peut rendre une vieille reponse.
Function SantePid()
  SantePid = 0
  On Error Resume Next
  Dim req, re, m
  Set req = CreateObject("MSXML2.ServerXMLHTTP.6.0")
  req.setTimeouts 2000, 2000, 2000, 2000
  req.Open "GET", url & "/api/health", False
  req.Send
  If Err.Number = 0 And req.Status = 200 Then
    Set re = New RegExp
    re.Pattern = """pid""\s*:\s*(\d+)"
    Set m = re.Execute(req.responseText)
    If m.Count > 0 Then SantePid = CLng(m(0).SubMatches(0))
  End If
  On Error GoTo 0
End Function

' Vrai si le processus pid est ne apres depart, donc lance par CE lanceur.
Function ProcessusNeuf(pid, depart)
  ProcessusNeuf = False
  If pid <= 0 Then Exit Function
  On Error Resume Next
  Dim procs, p, t
  Set procs = GetObject("winmgmts:\\.\root\cimv2").ExecQuery( _
    "SELECT CreationDate FROM Win32_Process WHERE ProcessId = " & pid)
  Set t = CreateObject("WbemScripting.SWbemDateTime")
  For Each p In procs
    t.Value = p.CreationDate
    If Err.Number = 0 Then
      If t.GetVarDate(True) >= depart Then ProcessusNeuf = True
    End If
  Next
  On Error GoTo 0
End Function

' Le dossier de donnees, comme config._data_root : DEEPOTUS_DATA_DIR s'il est pose, sinon
' %LOCALAPPDATA%\DeepotusVideoGenData.
Function DataRoot()
  Dim d
  d = Trim(shell.ExpandEnvironmentStrings("%DEEPOTUS_DATA_DIR%"))
  If d = "" Or d = "%DEEPOTUS_DATA_DIR%" Then d = shell.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\DeepotusVideoGenData"
  DataRoot = d
End Function

' HOST lu dans le .env : DEUX valeurs seulement (127.0.0.1, 0.0.0.0), la DERNIERE ligne HOST= gagne (comme
' python-dotenv) ; toute autre valeur, un fichier absent ou illisible -> 127.0.0.1. Option Explicit : chaque
' variable est declaree (une variable non declaree empecherait l'app de DEMARRER).
Function LireHote(chemin)
  Dim f, ligne, cand, hote
  hote = "127.0.0.1"
  If fso.FileExists(chemin) Then
    On Error Resume Next
    Set f = fso.OpenTextFile(chemin, 1)
    If Err.Number = 0 Then
      Do Until f.AtEndOfStream
        ligne = Trim(f.ReadLine)
        If Left(ligne, 4) = "HOST" And InStr(ligne, "=") > 0 Then
          If Trim(Left(ligne, InStr(ligne, "=") - 1)) = "HOST" Then
            cand = Trim(Mid(ligne, InStr(ligne, "=") + 1))
            If cand = "0.0.0.0" Or cand = "127.0.0.1" Then hote = cand Else hote = "127.0.0.1"
          End If
        End If
      Loop
      f.Close
    End If
    On Error GoTo 0
  End If
  LireHote = hote
End Function

' Stop a previously-launched backend so this run starts fresh. scripts\stop.ps1 finds it by its COMMAND
' LINE (uvicorn app.main:app --port 8765, python under this app folder) with its children, never the
' process of another application, and waits until the port no longer answers in HTTP (t386). Always
' run, even when /api/health is silent: a backend still booting would otherwise keep the port.
Sub StopExistingBackend()
  Dim rc
  On Error Resume Next
  rc = shell.Run("powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File """ & _
                 appDir & "\scripts\stop.ps1"" -Port 8765 -AppDir """ & appDir & """", 0, True)
  If Err.Number <> 0 Then rc = 1
  On Error GoTo 0
  If rc <> 0 And HealthOk() Then
    MsgBox "Port 8765 is used by another program, which was left running." & vbCrLf & _
           "Close it, then start the app again.", _
           vbExclamation, "Deepotus Video Gen"
    WScript.Quit 1
  End If
End Sub
