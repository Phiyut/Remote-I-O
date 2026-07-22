#define MyAppName "ROVENTO Repair WebApp"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "ROVENTO"
#define MyAppExeName "ROVENTO-Repair-WebApp.exe"
#define MyAppPort "5058"
#define MyFirewallRule "ROVENTO Repair WebApp Port 5058"

[Setup]
AppId={{9DD8A1FC-42F8-4D29-8BF7-0A33A688E307}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\ROVENTO\Repair WebApp
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer_output
OutputBaseFilename=ROVENTO_Repair_WebApp_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=yes
RestartApplications=no
UsePreviousAppDir=yes
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "startup"; Description: "Start the web server automatically when Windows starts"; GroupDescription: "Startup:"; Flags: checkedonce
Name: "lanfirewall"; Description: "Allow computers on the LAN to access TCP port {#MyAppPort}"; GroupDescription: "Network:"; Flags: checkedonce

[Files]
Source: "dist\ROVENTO-Repair-WebApp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Registry]
Root: HKLM; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "ROVENTORepairWebApp"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: startup; Flags: uninsdeletevalue

[Run]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#MyFirewallRule}"""; Flags: runhidden waituntilterminated; Tasks: lanfirewall
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#MyFirewallRule}"" dir=in action=allow protocol=TCP localport={#MyAppPort} profile=any"; Flags: runhidden waituntilterminated; Tasks: lanfirewall
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""{#MyAppExeName}"""; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#MyFirewallRule}"""; Flags: runhidden waituntilterminated

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  PS: String;
  Cmd: String;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM "{#MyAppExeName}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  PS := ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe');
  Cmd := '-NoProfile -ExecutionPolicy Bypass -Command "$ids = Get-NetTCPConnection -LocalPort {#MyAppPort} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($id in $ids) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }"';
  Exec(PS, Cmd, '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
