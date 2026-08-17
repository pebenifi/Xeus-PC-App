# Windows maintainer freeze. End users run XeusGUI-Setup.exe — no Python.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$py = $null
foreach ($candidate in @(".\venv\Scripts\python.exe", ".\.venv\Scripts\python.exe")) {
    if (Test-Path $candidate) { $py = $candidate; break }
}
if (-not $py) {
    Write-Error "Build venv with PySide6 + PyInstaller is required on the build machine. End users do not install Python."
}

& $py -m PyInstaller XeusGUI.spec --noconfirm --clean
Write-Host "Onedir app: $Root\dist\XeusGUI\XeusGUI.exe"

$iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($iscc) {
    & $iscc "installer\xeusgui.iss"
    Write-Host "Installer: $Root\dist\XeusGUI-Setup.exe"
} else {
    Write-Host "Inno Setup not found; zip the dist\XeusGUI folder or install Inno to build XeusGUI-Setup.exe"
}
