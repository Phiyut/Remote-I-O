#define MyAppName "ROVENTO Repair WebApp"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Supavut Industry Co., Ltd."
#define MyAppExeName "ROVENTO-Repair-Server.exe"
#define MyAppPort "5058"
#define MyTaskName "ROVENTO Repair WebApp Server"
#define MyFirewallName "ROVENTO Repair WebApp TCP 5058"

[Setup]
AppId={{DA9B5880-447F-4FA4-B38B-75AE3B80648B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
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
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "desktopicon"; Description: "Create desktop shortcut"; Flags: unchecked
Name: "autostart"; Description: "Start Web Server automatically when Windows user logs in"; Flags: checkedonce
Name: "lanfirewall"; Description: "Allow LAN access on TCP port {#MyAppPort}"; Flags: checkedonce

[Files]
Source: "dist\ROVENTO-Repair-WebApp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/c start """" ""http://127.0.0.1:{#MyAppPort}/"""; WorkingDir: "{app}"
Name: "{autoprograms}\Start {#MyAppName} Server"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--no-browser"; WorkingDir: "{app}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/c start """" ""http://127.0.0.1:{#MyAppPort}/"""; Tasks: desktopicon

[Run]
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""{#MyTaskName}"" /F"; Flags: runhidden waituntilterminated; Tasks: autostart
Filename: "{sys}\schtasks.exe"; Parameters: "/Create /TN ""{#MyTaskName}"" /SC ONLOGON /RL HIGHEST /TR ""'""{app}\{#MyAppExeName}"" --no-browser'"" /F"; Flags: runhidden waituntilterminated; Tasks: autostart
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#MyFirewallName}"""; Flags: runhidden waituntilterminated; Tasks: lanfirewall
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""{#MyFirewallName}"" dir=in action=allow protocol=TCP localport={#MyAppPort} profile=any"; Flags: runhidden waituntilterminated; Tasks: lanfirewall
Filename: "{app}\{#MyAppExeName}"; Description: "Start {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\taskkill.exe"; Parameters: "/F /IM ""{#MyAppExeName}"""; Flags: runhidden waituntilterminated
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN ""{#MyTaskName}"" /F"; Flags: runhidden waituntilterminated
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""{#MyFirewallName}"""; Flags: runhidden waituntilterminated

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /IM "{#MyAppExeName}"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Result := '';
end;
