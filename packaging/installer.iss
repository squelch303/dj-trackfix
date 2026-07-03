; dj-trackfix Windows installer
; Build with Inno Setup 6 (free, https://jrsoftware.org/isinfo.php):
;   1. Run build_windows.bat first to produce dist\dj-trackfix-gui\
;   2. Copy ffmpeg.exe into dist\dj-trackfix-gui\ (see BUILD.md)
;   3. Open this file in Inno Setup Compiler and click Build,
;      or from the command line:
;        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer.iss
;      Override the version (e.g. from a CI tag) with:
;        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /DMyAppVersion=1.2.3 packaging\installer.iss
;
; Output: packaging\output\dj-trackfix-<version>-setup.exe

#define MyAppName "dj-trackfix"
#ifndef MyAppVersion
  #define MyAppVersion "0.3.1"
#endif
#define MyAppPublisher "squelch303"
#define MyAppURL "https://github.com/squelch303/dj-trackfix"
#define MyAppExeName "dj-trackfix-gui.exe"

[Setup]
; Fixed GUID — do not change between releases, it's what lets Inno Setup
; detect an existing install and upgrade it cleanly instead of installing
; side-by-side.
AppId={{D5F4F27B-D333-4376-B45B-713B2E9C96DE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
; Per-user install location — no admin rights / UAC prompt required.
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=dj-trackfix-{#MyAppVersion}-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Replace with a real .ico if you have one; comment out if not.
; SetupIconFile=trackfix.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; Everything PyInstaller produced, including the ffmpeg.exe you copied in.
Source: "..\dist\dj-trackfix-gui\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
