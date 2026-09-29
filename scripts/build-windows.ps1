param(
    [string]$Python = ".\.venv\Scripts\python.exe",
    [string]$Iscc = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    [switch]$BundleOnly
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath $Python)) { throw "Python missing: $Python" }
& $Python -c "import platform, struct, sys; sys.exit(0 if sys.platform == 'win32' and struct.calcsize('P') == 8 and platform.machine().upper() in ('AMD64', 'X86_64') else 1)"
if ($LASTEXITCODE -ne 0) { throw "This installer requires Windows x64 Python" }
& $Python -m unittest discover -s tests -q
if ($LASTEXITCODE -ne 0) { throw "Regression tests failed" }
& $Python -m PyInstaller --noconfirm packaging/DigitalWellbeingTracker.spec
if ($LASTEXITCODE -ne 0) { throw "Application bundle failed" }
$report = Join-Path (Get-Location) "dist/bundle-check.json"
if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
$check = Start-Process -FilePath "dist/DigitalWellbeingTracker/DigitalWellbeingTracker.exe" -ArgumentList @('--self-test', ('"' + $report + '"')) -WindowStyle Hidden -PassThru
if (-not $check.WaitForExit(120000)) { Stop-Process -Id $check.Id; throw "Bundled application check timed out" }
if ($check.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $report)) { throw "Bundled application check failed; see $report" }
if (-not (Get-Content -LiteralPath $report -Raw | ConvertFrom-Json).ok) { throw "Bundled application check failed" }
if ($BundleOnly) { return }
if (-not (Test-Path -LiteralPath $Iscc)) { throw "Install Inno Setup 6 or pass -Iscc with its compiler path" }
$version = (Get-Content packaging/desktop-version.txt -Raw).Trim()
& $Iscc "/DAppVersion=$version" packaging/installer.iss
if ($LASTEXITCODE -ne 0) { throw "Installer compilation failed" }
$setup = "dist/installer/DigitalWellbeingTracker-$version-Setup-x64.exe"
(Get-FileHash -LiteralPath $setup -Algorithm SHA256).Hash + '  ' + (Split-Path $setup -Leaf) | Set-Content -Encoding ascii "$setup.sha256"
Write-Output "Built $setup"
