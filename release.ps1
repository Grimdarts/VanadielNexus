# Ships a new version to every player.
#   .\release.ps1 1.3.0
# Bumps APP_VERSION, commits, tags v1.3.0 and pushes. GitHub Actions then builds the exe and
# publishes a Release; each player's app sees it on next launch and offers to update.
param(
    [Parameter(Mandatory = $true)][string]$Version
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw 'Version must look like 1.3.0' }
if (git status --porcelain) { throw 'Commit or stash your changes first.' }

$file = 'vanadielnexus_overlay.py'
$text = [IO.File]::ReadAllText("$PSScriptRoot\$file")
$new = [regex]::Replace($text, '(?m)^APP_VERSION = ".*"$', "APP_VERSION = `"$Version`"")
if ($new -eq $text) { throw "APP_VERSION is already $Version (or wasn't found)" }
[IO.File]::WriteAllText("$PSScriptRoot\$file", $new, (New-Object Text.UTF8Encoding $false))

git add $file
git commit -m "Release v$Version"
git tag "v$Version"
git push origin main "v$Version"
Write-Host "Pushed v$Version. Watch the build: https://github.com/Grimdarts/VanadielNexus/actions"
