; Inno Setup script for the InkTrack Windows desktop app.
;
; Produces a per-user installer (no admin required) that installs the single
; PyInstaller-built InkTrack.exe, adds Start-menu/uninstall entries, and
; bootstraps the Microsoft Edge WebView2 Evergreen runtime when missing.
;
; User data lives in {localappdata}\InkTrack (created by the app at runtime);
; it is intentionally NOT removed on uninstall so projects/photos survive
; upgrades and reinstalls.
;
; Compile (from the repo root) once InkTrack.exe has been built by PyInstaller:
;     iscc desktop\installer.iss
; CI may download MicrosoftEdgeWebview2Setup.exe into desktop\ first so it can
; be bundled; if it is absent the installer still compiles and simply relies on
; the runtime already being present (it is preinstalled on Windows 11).

#define AppName "InkTrack"
#define AppPublisher "codebyit"
#define AppURL "https://github.com/codebyit/inktracker"

; Pull the version from the single-source-of-truth VERSION file.
#ifndef AppVersion
  #define AppVersion Trim(FileRead(FileOpen("..\VERSION")))
#endif

; Optional WebView2 Evergreen bootstrapper (bundled only if present at compile).
#define WV2Setup "MicrosoftEdgeWebview2Setup.exe"
#define HasWV2 FileExists(WV2Setup)

; Directory that holds the PyInstaller output (the InkTrack\ onedir folder and
; the produced installer). Relative values are resolved against THIS script's
; directory (desktop\). Overridable so CI can pass an absolute path via
; /DDistDir=...; defaults to the local build sandbox (sibling of the repo).
#ifndef DistDir
  #define DistDir "..\..\inktrack-windows\dist"
#endif

[Setup]
AppId={{7C9A1F2E-3B4D-4E5F-9A1B-2C3D4E5F6A7B}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={localappdata}\Programs\InkTrack
DisableProgramGroupPage=yes
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
OutputDir={#DistDir}
OutputBaseFilename=InkTrack-Setup-{#AppVersion}
SetupIconFile=inktrack.ico
UninstallDisplayIcon={app}\InkTrack.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#DistDir}\InkTrack\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
#if HasWV2
Source: "{#WV2Setup}"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: WebView2Missing
#endif

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\InkTrack.exe"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\InkTrack.exe"; Tasks: desktopicon

[Run]
#if HasWV2
Filename: "{tmp}\{#WV2Setup}"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2 runtime..."; Flags: waituntilterminated; Check: WebView2Missing
#endif
Filename: "{app}\InkTrack.exe"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
function WebView2Missing(): Boolean;
const
  ClientKey = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  ClientKeyWow = 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
var
  Version: String;
begin
  // The Evergreen WebView2 runtime publishes its version ('pv') under the
  // EdgeUpdate client GUID, per-machine (HKLM, incl. WOW6432Node) or per-user.
  Result := True;
  if RegQueryStringValue(HKLM, ClientKeyWow, 'pv', Version) and (Version <> '') then
    Result := False
  else if RegQueryStringValue(HKLM, ClientKey, 'pv', Version) and (Version <> '') then
    Result := False
  else if RegQueryStringValue(HKCU, ClientKey, 'pv', Version) and (Version <> '') then
    Result := False;
end;
