<#
.SYNOPSIS
    Creates (or refreshes) a "Qwythos" desktop shortcut that launches the
    native-window desktop app. Safe to re-run any time, e.g. after moving the
    repo to a new path.
#>

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$launcher = Join-Path $repoRoot 'desktop\launcher.pyw'
$icon = Join-Path $repoRoot 'static\static\qwythos.ico'

if (-not (Test-Path $launcher)) {
    throw "Could not find launcher.pyw at $launcher"
}

$pythonwCmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
if (-not $pythonwCmd) {
    $pythonCmd = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $pythonCmd) {
        throw 'Could not find python.exe or pythonw.exe on PATH. Install Python first.'
    }
    $pythonwPath = Join-Path (Split-Path -Parent $pythonCmd.Source) 'pythonw.exe'
    if (-not (Test-Path $pythonwPath)) {
        throw "Found python.exe at $($pythonCmd.Source) but no pythonw.exe alongside it."
    }
} else {
    $pythonwPath = $pythonwCmd.Source
}

$desktop = [Environment]::GetFolderPath('Desktop')
$shortcutPath = Join-Path $desktop 'Qwythos.lnk'

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = "`"$launcher`""
$shortcut.WorkingDirectory = $repoRoot
$shortcut.Description = 'Qwythos (native window)'
if (Test-Path $icon) {
    $shortcut.IconLocation = $icon
}
$shortcut.Save()

Write-Host "Created shortcut: $shortcutPath"
Write-Host "  Target: $pythonwPath"
Write-Host "  Arguments: `"$launcher`""
