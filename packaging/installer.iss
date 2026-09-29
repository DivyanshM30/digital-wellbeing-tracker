#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
[Setup]
AppId={{CC47581B-D48C-48ED-9908-CE8736F6B731}
AppName=Digital Wellbeing Tracker
AppVersion={#AppVersion}
AppPublisher=Divyansh Mishra
AppPublisherURL=https://github.com/DivyanshM30/digital-wellbeing-tracker
DefaultDirName={localappdata}\Programs\DigitalWellbeingTracker
DisableDirPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DefaultGroupName=Digital Wellbeing Tracker
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=DigitalWellbeingTracker-{#AppVersion}-Setup-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\DigitalWellbeingTracker.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\dist\DigitalWellbeingTracker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Digital Wellbeing Tracker"; Filename: "{app}\DigitalWellbeingTracker.exe"
Name: "{autodesktop}\Digital Wellbeing Tracker"; Filename: "{app}\DigitalWellbeingTracker.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DigitalWellbeingTracker.exe"; Description: "Open Digital Wellbeing Tracker"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  Value: String;
  Expected: String;
begin
  if CurUninstallStep = usUninstall then begin
    Expected := '"' + ExpandConstant('{app}\DigitalWellbeingTracker.exe') + '" --startup';
    if RegQueryStringValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'DigitalWellbeingTracker', Value) then
      if (CompareText(Value, Expected) = 0) or
         (CompareText(Value, ExpandConstant('{app}\DigitalWellbeingTracker.exe') + ' --startup') = 0) then
        RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run', 'DigitalWellbeingTracker');
  end;
end;
