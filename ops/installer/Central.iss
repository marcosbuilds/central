#define AppName "Central Colaborativa"
#define AppVersion "0.2.0"
#define AppPublisher "Central"

[Setup]
AppId={{6A6A9B2C-1E01-4D55-9C0A-52B74D1E0A10}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\Central Colaborativa
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\artifacts\installer
OutputBaseFilename=Central-Colaborativa-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\Central.exe
SetupLogging=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\Central.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Central.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\Central.exe"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent
