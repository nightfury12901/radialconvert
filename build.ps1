# Build RadialConvert on Windows.  Usage:  .\build.ps1 [-Version 1.0.0]
# Produces dist\RadialConvert\RadialConvert.exe and, if Inno Setup is installed, dist\RadialConvert-Setup-<version>.exe
param([string]$Version = "1.0.0")
$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt pyinstaller
python tools\make_icon.py
python tools\fetch_tools.py
pyinstaller RadialConvert.spec --noconfirm

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    $candidate = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $candidate) { $iscc = $candidate }
}
if ($iscc) {
    & $iscc "/DAppVersion=$Version" installer.iss
    Write-Host "Installer: dist\RadialConvert-Setup-$Version.exe"
} else {
    Write-Host "Inno Setup not found. Install it from https://jrsoftware.org/isdl.php to build the installer."
    Write-Host "The app itself is ready: dist\RadialConvert\RadialConvert.exe"
}
