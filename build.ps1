# Rebuilds VanadielNexus.exe from source and swaps it into place.
# Closes a running copy first (Windows can't overwrite a running exe) and relaunches it afterwards.
# Runs automatically after each commit that changes app code (see tools/hooks/post-commit).
param(
    [switch]$NoLaunch
)

# Native tools write progress to stderr; check exit codes instead of stopping on it
$ErrorActionPreference = 'Continue'
Set-Location $PSScriptRoot

# Find Python ("python" on many PCs is just the Microsoft Store alias, so prefer the py launcher)
if (Get-Command py -ErrorAction SilentlyContinue) { $pyExe = 'py'; $pyArgs = @('-3') }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $pyExe = 'python'; $pyArgs = @() }
else { throw 'Python not found. Install Python 3 from python.org.' }

function Invoke-Py { & $pyExe @pyArgs @args }

Invoke-Py -m PyInstaller --version *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing PyInstaller...'
    Invoke-Py -m pip install --user pyinstaller
}

Write-Host 'Building VanadielNexus.exe...'
Invoke-Py -m PyInstaller --noconfirm --log-level WARN VanadielNexus.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed (exit $LASTEXITCODE)" }

$built = Join-Path $PSScriptRoot 'dist\VanadielNexus.exe'
$target = Join-Path $PSScriptRoot 'VanadielNexus.exe'

$running = Get-Process VanadielNexus -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $target }
if ($running) {
    Write-Host 'Closing running VanadielNexus...'
    $running | Stop-Process -Force
    $running | Wait-Process -Timeout 15 -ErrorAction SilentlyContinue
}

# The onefile bootloader can hold the exe for a moment after exit, so retry the copy
for ($i = 0; $i -lt 20; $i++) {
    try { Copy-Item $built $target -Force -ErrorAction Stop; break }
    catch { Start-Sleep -Milliseconds 500 }
}
if ($i -ge 20) { throw "Could not replace $target (still in use?)" }

Write-Host "Updated $target"
if ($running -and -not $NoLaunch) {
    Start-Process $target
    Write-Host 'Relaunched VanadielNexus.'
}
