; Inno Setup script. Build with:  iscc /DAppVersion=1.0.0 installer.iss   (run build.ps1 first)
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{8F3A6B52-5C1D-4E7A-9B0E-52A4D6C1E7F1}
AppName=RadialConvert
AppVersion={#AppVersion}
AppPublisher=RadialConvert
DefaultDirName={autopf}\RadialConvert
DefaultGroupName=RadialConvert
; Per-user install: no admin prompt, and the right-click entry goes in HKCU.
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=RadialConvert-Setup-{#AppVersion}
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\RadialConvert.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=yes

[Tasks]
Name: "contextmenu"; Description: "Add ""Convert with RadialConvert"" to the right-click menu"
Name: "startup"; Description: "Start RadialConvert when Windows starts"
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "dist\RadialConvert\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\RadialConvert"; Filename: "{app}\RadialConvert.exe"
Name: "{autodesktop}\RadialConvert"; Filename: "{app}\RadialConvert.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\*\shell\RadialConvert"; ValueType: string; ValueData: "Convert with RadialConvert"; Flags: uninsdeletekey; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\RadialConvert"; ValueType: string; ValueName: "Icon"; ValueData: "{app}\RadialConvert.exe"; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Classes\*\shell\RadialConvert\command"; ValueType: string; ValueData: """{app}\RadialConvert.exe"" ""%1"""; Tasks: contextmenu
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "RadialConvert"; ValueData: """{app}\RadialConvert.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\RadialConvert.exe"; Description: "Start RadialConvert now"; Flags: nowait postinstall skipifsilent
