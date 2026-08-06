; ============================================================
;  DEEPOTUS VIDEO GEN - Windows installer (v1.15.0)
;
;  Packages the complete, already-built app tree (embedded Python
;  runtime + bundled ffmpeg + patched frontend + backend) into a
;  single per-user setup .exe with ZERO prerequisites for the buyer.
;
;  User DATA (keys, images, renders, db) lives separately in
;  %LOCALAPPDATA%\DeepotusVideoGenData and is NEVER touched by this
;  installer or its uninstaller — it survives install / uninstall /
;  upgrade. Use Importer-mes-donnees.ps1 to bring data to a new PC.
; ============================================================

#define MyAppName "Deepotus Video Gen"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "Deepotus"
; StageDir est normalement fourni par build-installer.ps1 via /DStageDir=<...>
; (stage court, D:\dz par défaut). Le define ci-dessous n'est qu'un secours
; pour une compilation manuelle — un define en dur écraserait le /D et ferait
; échouer ISCC sur un stage inexistant (incident build v1.16.0).
#ifndef StageDir
  #define StageDir "D:\dz"
#endif
#define AppRoot StageDir + "\app"

[Setup]
AppId={{A3F1C2D4-5E6B-47A8-9C0D-1E2F3A4B5C6D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\DeepotusVideoGen
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
DisableDirPage=yes
PrivilegesRequired=lowest
OutputDir=C:\Users\olivi\OneDrive\Bureau\DeepotusVideoGen-Export
OutputBaseFilename=DeepotusVideoGen-Setup-{#MyAppVersion}
; Customer-facing EULA. The repo LICENSE is the SOURCE licence and grants a
; buyer nothing — this is the agreement the purchaser actually accepts, and
; it must be shown at install time before any file is written.
LicenseFile={#SourcePath}\EULA.txt
SetupIconFile={#AppRoot}\assets\deepotus-logo.ico
UninstallDisplayIcon={app}\assets\deepotus-logo.ico
UninstallDisplayName={#MyAppName} {#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
VersionInfoVersion={#MyAppVersion}
VersionInfoProductVersion={#MyAppVersion}

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[InstallDelete]
; Clean stale app files from any previous install BEFORE copying the new ones,
; so the browser never loads an old frontend bundle and Python never loads
; stale bytecode. User DATA lives in %LOCALAPPDATA%\DeepotusVideoGenData and is
; NEVER touched here.
Type: filesandordirs; Name: "{app}\frontend\dist\assets"
Type: filesandordirs; Name: "{app}\backend\app\__pycache__"
Type: filesandordirs; Name: "{app}\backend\app\api\__pycache__"
Type: filesandordirs; Name: "{app}\backend\app\services\__pycache__"
Type: filesandordirs; Name: "{app}\backend\app\models\__pycache__"

[Files]
Source: "{#AppRoot}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\launch-silent.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\deepotus-logo.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\launch-silent.vbs"""; WorkingDir: "{app}"; IconFilename: "{app}\assets\deepotus-logo.ico"; Tasks: desktopicon

[Run]
Filename: "{sys}\wscript.exe"; Parameters: """{app}\scripts\launch-silent.vbs"""; Description: "{cm:LaunchProgram,{#MyAppName}}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
