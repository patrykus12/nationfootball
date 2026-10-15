; Instalator NationFootball (Inno Setup 6) - budowany automatycznie przez build.py
; Instaluje dla bieĹĽÄ…cego uĹĽytkownika, bez uprawnieĹ„ administratora.

#define Wersja "1.1"

[Setup]
; AppId nie moĹĽe siÄ™ zmieniaÄ‡ miÄ™dzy wersjami - po nim Windows rozpoznaje aktualizacjÄ™
AppId={{27C07EC7-5E49-4119-B2ED-D620FA8BEDBA}
AppName=NationFootball
AppVersion={#Wersja}
AppPublisher=patrykus12
DefaultDirName={localappdata}\Programs\NationFootball
DefaultGroupName=NationFootball
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=wydanie
OutputBaseFilename=NationFootball_Instalator
SetupIconFile=ball.ico
UninstallDisplayIcon={app}\NationFootball.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Tasks]
Name: "skrot_pulpit"; Description: "UtwĂłrz skrĂłt na pulpicie"; GroupDescription: "SkrĂłty:"

[Files]
Source: "dist\NationFootball.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\NationFootball"; Filename: "{app}\NationFootball.exe"
Name: "{group}\Odinstaluj NationFootball"; Filename: "{uninstallexe}"
Name: "{userdesktop}\NationFootball"; Filename: "{app}\NationFootball.exe"; Tasks: skrot_pulpit

[Run]
Filename: "{app}\NationFootball.exe"; Description: "Uruchom NationFootball"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; dane pobrane przez aplikacjÄ™ (mecze, skĹ‚ady, flagi) - patrz KATALOG_PROJEKTU w test_flashscore.py
Type: filesandordirs; Name: "{localappdata}\NationFootball"
