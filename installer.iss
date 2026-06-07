#define MyAppName "SC Dossier"
#define MyAppVersion "0.4.2" ; Will be dynamically replaced by build.py
#define MyAppPublisher "PINKgeekPDX"
#define MyAppURL "https://github.com/PINKgeekPDX/SCDossier"
#define MyAppExeName "SCDossier.exe"
#define MyAppDataDir "{userdocs}\PINK\SCDossier"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{5C0A7B9B-D5A4-4A3C-9F8C-4B7E7A1C2D3B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=SCDossier-Setup
SetupIconFile=src\assets\appicon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Allow user to choose install directory
DisableDirPage=no
; Show info page after install with UAC reminder
InfoAfterMessage=SC Dossier has been installed successfully.{#crlf}{#crlf}IMPORTANT: If Star Citizen is running with Administrator privileges (UAC elevated),{#crlf}you MUST also run SC Dossier as Administrator for the global hotkeys to work.{#crlf}{#crlf}Right-click SCDossier.exe and select "Run as administrator", or set it{#crlf}permanently in Properties > Compatibility > "Run this program as an administrator".
; Code signing via signtool — only active when build.py passes /dENABLE_SIGNING=1
#ifdef ENABLE_SIGNING
SignTool=signtool /fd SHA256 /tr http://timestamp.digicert.com /td SHA256
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\SCDossier\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\SCDossier\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Remove app data directories on uninstall (user is prompted by Inno Setup)
Type: filesandordirs; Name: "{#MyAppDataDir}\Cache"
Type: filesandordirs; Name: "{#MyAppDataDir}\Logs"

[UninstallRun]
; Clean up leftover data directory contents if empty
Filename: "{cmd}"; Parameters: "/C rmdir /s /q ""{#MyAppDataDir}\Cache"" 2>nul"; Flags: runhidden
Filename: "{cmd}"; Parameters: "/C rmdir /s /q ""{#MyAppDataDir}\Logs"" 2>nul"; Flags: runhidden
Filename: "{cmd}"; Parameters: "/C rmdir ""{#MyAppDataDir}"" 2>nul"; Flags: runhidden
