; Copyright (C) 2026 Viktor Podust
; SPDX-License-Identifier: GPL-3.0-or-later

; The Windows installer (Inno Setup 6), made by scripts/build.py, which gives it:
;   Version      the version, as written: 1.2.0, 1.2.0-beta.2
;   Numbers      just its numbers, for Windows' file properties: 1.2.0
;   Source       the folder PyInstaller made
;   OutputDir    where the installer goes
;   OutputName   its file name, without .exe
;   Icon         the .ico file
; It installs for the current user only (no administrator rights asked), with a Start menu entry, an optional desktop
; one and an uninstaller, in English or Russian (as Windows is). The AppId never changes: it's how Windows knows a
; newer version is the same application. Project files (.cubenet) open with it when double-clicked, and have its icon;
; the uninstaller takes that away again.

#ifndef Version
  #error Give the version: /DVersion=1.2.0
#endif

[Setup]
AppId={{0554B29B-25AF-4364-969F-0AD244EAC194}
AppName=Cube Net
AppVersion={#Version}
AppVerName=Cube Net {#Version}
AppPublisher=Viktor Podust
AppPublisherURL=https://github.com/Avorthoren/cube-net
AppSupportURL=https://github.com/Avorthoren/cube-net
AppUpdatesURL=https://github.com/Avorthoren/cube-net/releases
AppCopyright=Copyright (C) 2026 Viktor Podust
VersionInfoVersion={#Numbers}
DefaultDirName={autopf}\Cube Net
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename={#OutputName}
SetupIconFile={#Icon}
UninstallDisplayIcon={app}\Cube Net.exe
UninstallDisplayName=Cube Net
WizardStyle=modern
Compression=lzma2/max
SolidCompression=yes
CloseApplications=yes
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#Source}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[InstallDelete]
; What an earlier version left there (its files may differ from this one's).
Type: filesandordirs; Name: "{app}\_internal"

[Registry]
; .cubenet files are Cube Net projects ("HKA": the current user's part of the registry, for an install for them).
Root: HKA; Subkey: "Software\Classes\.cubenet"; ValueType: string; ValueName: ""; ValueData: "CubeNet.Project"; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.cubenet\OpenWithProgids"; ValueType: string; ValueName: "CubeNet.Project"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\CubeNet.Project"; ValueType: string; ValueName: ""; ValueData: "Cube Net project"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\CubeNet.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\Cube Net.exe,0"
Root: HKA; Subkey: "Software\Classes\CubeNet.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\Cube Net.exe"" ""%1"""

[Icons]
Name: "{autoprograms}\Cube Net"; Filename: "{app}\Cube Net.exe"
Name: "{autodesktop}\Cube Net"; Filename: "{app}\Cube Net.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Cube Net.exe"; Description: "{cm:LaunchProgram,Cube Net}"; Flags: nowait postinstall skipifsilent
