#define MyAppName "SC Dossier"
#define MyAppVersion "1.0.0" ; Will be dynamically replaced by build.py
#define MyAppPublisher "PINKgeekPDX"
#define MyAppURL "https://github.com/PINKgeekPDX/SCDossier"
#define MyAppExeName "SCDossier.exe"
#define MyAppDataDir "{userdocs}\PINK\SCDossier"

[Setup]
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
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Allow user to choose install directory
DisableDirPage=no
; Show info page after install with UAC reminder
InfoAfterFile=infoafter.txt
; Code signing via signtool — only active when build.py passes /dENABLE_SIGNING=1
#ifdef ENABLE_SIGNING
SignTool=signtool $f
SignedUninstaller=yes
#endif

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
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
