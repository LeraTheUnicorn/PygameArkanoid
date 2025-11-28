; Скрипт Inno Setup для создания инсталлятора игры Арканоид
; Для компиляции требуется Inno Setup Compiler

#define MyAppName "Arkanoid"
#define MyAppVersion "1.6.2"
#define MyAppPublisher "Developer"
#define MyAppURL "https://github.com/developer/arkanoid"
#define MyAppExeName "Arkanoid_v{#MyAppVersion}.exe"

[Setup]
; Основные настройки
AppId={{12345678-1234-1234-1234-123456789012}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\Games\Arkanoid
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
InfoBeforeFile=docs/README_RELEASE.txt
OutputDir=installer
OutputBaseFilename=Arkanoid_v{#MyAppVersion}_Setup
SetupIconFile=resources/icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}": Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}": Flags: unchecked; OnlyBelowVersion: 6.1
Name: "gamerecords"; Description: "Создать папку для сохранения рекордов игрока"; GroupDescription: "Настройки игры": Flags: checked

[Files]
Source: "Arkanoid_v{#MyAppVersion}.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "sounds\*"; DestDir: "{app}\sounds"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "images\*"; DestDir: "{app}\images"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "resources\highscores.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "highscores.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "docs\README_RELEASE.md"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Добавляем запись в реестр для корректной деинсталляции
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arkanoid"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arkanoid"; ValueType: string; ValueName: "DisplayVersion"; ValueData: "{#MyAppVersion}"
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arkanoid"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arkanoid"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arkanoid"; ValueType: dword; ValueName: "NoModify"; ValueData: 1
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\Arkanoid"; ValueType: dword; ValueName: "NoRepair"; ValueData: 1

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: runascurrentuser postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\Games\Arkanoid\highscores.json"

[UninstallRun]
Filename: "{cmd}"; Parameters: "/c rmdir /s /q ""{localappdata}\Games\Arkanoid"""; Flags: runascurrentuser

[Code]
function InitializeSetup(): Boolean;
var
  V: Integer;
  iResultCode: Integer;
  sPath: String;
begin
  Result := True;
  
  // Создаем директорию для игры, если она не существует
  sPath := ExpandConstant('{localappdata}\Games\Arkanoid');
  if not DirExists(sPath) then
    CreateDir(sPath);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Создаем пустой файл рекордов, если он не существует
    if not FileExists(ExpandConstant('{localappdata}\Games\Arkanoid\highscores.json')) then
      SaveStringToFile(ExpandConstant('{localappdata}\Games\Arkanoid\highscores.json'), '[]', False);
  end;
end;

function InitializeSetup(): Boolean;
var
  V: Integer;
begin
  Result := True;
  
  // Проверяем версию Windows
  if not RegQueryDWordValue(HKLM, 'SOFTWARE\Microsoft\Windows NT\CurrentVersion', 'ProductVersion', V) then
  begin
    MsgBox('Не удалось определить версию Windows. Установка продолжена.', mbWarning, MB_OK);
  end;
end;