# Creates "E-Basura Mo" shortcut on the user's Desktop (one-click launch).
$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Launcher = Join-Path $ProjectDir "Start E-Basura Mo.bat"

if (-not (Test-Path $Launcher)) {
    Write-Error "Launcher not found: $Launcher"
}

$Desktop = [Environment]::GetFolderPath("Desktop")
$Wsh = New-Object -ComObject WScript.Shell

# Main app shortcut
$Main = $Wsh.CreateShortcut((Join-Path $Desktop "E-Basura Mo.lnk"))
$Main.TargetPath = $Launcher
$Main.WorkingDirectory = $ProjectDir
$Main.WindowStyle = 7   # Minimized (hides cmd flash)
$Main.Description = "E-Basura Mo - Barangay waste management (offline)"
$Main.Save()

# Optional kiosk shortcut
$Kiosk = $Wsh.CreateShortcut((Join-Path $Desktop "E-Basura Mo (Kiosk).lnk"))
$Kiosk.TargetPath = $Launcher
$Kiosk.Arguments = "kiosk"
$Kiosk.WorkingDirectory = $ProjectDir
$Kiosk.WindowStyle = 7
$Kiosk.Description = "E-Basura Mo - Resident kiosk mode (no login)"
$Kiosk.Save()

Write-Host "Created:"
Write-Host "  $Desktop\E-Basura Mo.lnk"
Write-Host "  $Desktop\E-Basura Mo (Kiosk).lnk"
