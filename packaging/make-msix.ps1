<#
.SYNOPSIS
    Build a Microsoft Store MSIX package for InkTrack from the PyInstaller
    onedir output.

.DESCRIPTION
    Lays out a package root (AppxManifest.xml with tokens filled in + Assets\ +
    the onedir InkTrack\ folder) and runs makeappx.exe to produce an .msix.

    The produced package is UNSIGNED — the Microsoft Store re-signs it on
    submission. Pass -SelfSign to sign it with a self-signed certificate for
    LOCAL sideload testing only (such packages will not install on other
    machines unless the cert is trusted there).

.PARAMETER OneDir
    Path to the PyInstaller onedir folder that contains InkTrack.exe (and the
    _internal\ payload). Default: dist\InkTrack relative to the repo root.

.PARAMETER Version
    Product version. Accepts 3-part (0.10.0) or 4-part (0.10.0.0); normalized to
    4-part for the MSIX Identity. Default: contents of the repo VERSION file.

.PARAMETER IdentityName
    MSIX Identity/Name (reserved in Partner Center), e.g. 12345Publisher.InkTrack.

.PARAMETER Publisher
    MSIX Identity/Publisher. MUST match your Partner Center publisher
    (CN=GUID-style) for Store submission, or the subject of your self-signed
    cert (e.g. "CN=Your Name") for sideload testing.

.PARAMETER PublisherDisplayName
    Human-readable publisher name shown in the Store.

.PARAMETER OutMsix
    Output .msix path. Default: InkTrack-<Version>.msix in the current directory.

.PARAMETER SelfSign
    Also sign the package with a self-signed certificate for local sideload.

.EXAMPLE
    # CI / Store submission (unsigned; Store signs on submission)
    ./packaging/make-msix.ps1 -OneDir dist/InkTrack -Version 0.10.0 `
        -IdentityName "12345Publisher.InkTrack" `
        -Publisher "CN=ABCDEF01-2345-6789-ABCD-EF0123456789" `
        -PublisherDisplayName "Your Name"

.EXAMPLE
    # Local sideload test (self-signed)
    ./packaging/make-msix.ps1 -SelfSign `
        -Publisher "CN=Your Name" -PublisherDisplayName "Your Name" `
        -IdentityName "InkTrack.Dev"
    Add-AppxPackage .\InkTrack-0.10.0.msix
#>
[CmdletBinding()]
param(
    [string]$OneDir,
    [string]$Version,
    [Parameter(Mandatory = $true)][string]$IdentityName,
    [Parameter(Mandatory = $true)][string]$Publisher,
    [string]$PublisherDisplayName = "InkTrack",
    [string]$OutMsix,
    [switch]$SelfSign
)

$ErrorActionPreference = "Stop"
$PackagingDir = $PSScriptRoot
$RepoRoot = Split-Path -Parent $PackagingDir

if (-not $OneDir) { $OneDir = Join-Path $RepoRoot "dist\InkTrack" }
if (-not (Test-Path (Join-Path $OneDir "InkTrack.exe"))) {
    throw "OneDir '$OneDir' does not contain InkTrack.exe. Build it first: pyinstaller desktop/inktrack.spec"
}

if (-not $Version) { $Version = (Get-Content (Join-Path $RepoRoot "VERSION") -Raw).Trim() }
# Normalize to a 4-part version for the MSIX Identity.
$parts = $Version.Split(".")
while ($parts.Count -lt 4) { $parts += "0" }
$Version4 = ($parts[0..3] -join ".")

if (-not $OutMsix) { $OutMsix = Join-Path (Get-Location) "InkTrack-$Version.msix" }

function Find-SdkTool([string]$tool) {
    $roots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    ) | Where-Object { Test-Path $_ }
    $candidates = foreach ($r in $roots) {
        Get-ChildItem -Path $r -Recurse -Filter $tool -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\" }
    }
    $picked = $candidates | Sort-Object FullName -Descending | Select-Object -First 1
    if (-not $picked) { throw "$tool not found. Install the Windows 10/11 SDK." }
    return $picked.FullName
}

$makeappx = Find-SdkTool "makeappx.exe"
Write-Host "Using makeappx: $makeappx"

# --- Stage the package root -------------------------------------------------
$Stage = Join-Path ([System.IO.Path]::GetTempPath()) ("inktrack_msix_" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $Stage | Out-Null
try {
    # Assets
    Copy-Item (Join-Path $PackagingDir "Assets") (Join-Path $Stage "Assets") -Recurse -Force
    # App payload (the onedir folder becomes InkTrack\ at the package root)
    Copy-Item $OneDir (Join-Path $Stage "InkTrack") -Recurse -Force

    # Manifest with tokens substituted
    $template = Get-Content (Join-Path $PackagingDir "AppxManifest.xml") -Raw
    $manifest = $template `
        -replace "\{\{IDENTITY_NAME\}\}", [System.Security.SecurityElement]::Escape($IdentityName) `
        -replace "\{\{PUBLISHER\}\}", [System.Security.SecurityElement]::Escape($Publisher) `
        -replace "\{\{PUBLISHER_DISPLAY_NAME\}\}", [System.Security.SecurityElement]::Escape($PublisherDisplayName) `
        -replace "\{\{VERSION\}\}", $Version4
    Set-Content -Path (Join-Path $Stage "AppxManifest.xml") -Value $manifest -Encoding UTF8

    Write-Host "Packing MSIX -> $OutMsix (Identity $IdentityName, Version $Version4)"
    & $makeappx pack /d $Stage /p $OutMsix /o
    if ($LASTEXITCODE -ne 0) { throw "makeappx failed with exit code $LASTEXITCODE." }
}
finally {
    Remove-Item $Stage -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Optional: self-sign for local sideload --------------------------------
if ($SelfSign) {
    $signtool = Find-SdkTool "signtool.exe"
    $certPath = Join-Path ([System.IO.Path]::GetTempPath()) "inktrack_selfsign.pfx"
    $pwd = ConvertTo-SecureString -String "inktrack" -Force -AsPlainText
    Write-Host "Creating self-signed certificate for $Publisher (sideload only)..."
    $cert = New-SelfSignedCertificate -Type Custom -Subject $Publisher `
        -KeyUsage DigitalSignature -FriendlyName "InkTrack Sideload" `
        -CertStoreLocation "Cert:\CurrentUser\My" `
        -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
    Export-PfxCertificate -Cert $cert -FilePath $certPath -Password $pwd | Out-Null
    & $signtool sign /fd SHA256 /a /f $certPath /p "inktrack" $OutMsix
    if ($LASTEXITCODE -ne 0) { throw "signtool failed with exit code $LASTEXITCODE." }
    Write-Host "Self-signed. To trust the cert for sideload, import it into the"
    Write-Host "Local Machine 'Trusted People' store, then: Add-AppxPackage '$OutMsix'"
}

Write-Host "Done: $OutMsix"
