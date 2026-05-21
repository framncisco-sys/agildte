# Crea en el Escritorio un acceso directo "AgilDTE - Punto de venta" con icono del logo.
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Bat = Join-Path $ScriptDir 'iniciar_chrome_pos_impresion_silenciosa.bat'
$Ico = Join-Path $ScriptDir 'agildte_pos.ico'
$Png = Join-Path $ScriptDir 'agildte_pos_logo.png'

function Ensure-Icon {
    if (Test-Path -LiteralPath $Ico) { return }
    if (-not (Test-Path -LiteralPath $Png)) {
        throw "No existe $Ico ni $Png. Copie el logo como agildte_pos_logo.png en la carpeta scripts."
    }
    Add-Type -AssemblyName System.Drawing
    $img = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $Png))
    $size = [Math]::Min(256, [Math]::Min($img.Width, $img.Height))
    $bmp = New-Object System.Drawing.Bitmap $size, $size
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.Clear([System.Drawing.Color]::White)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($img, 0, 0, $size, $size)
    $img.Dispose()
    $hIcon = $bmp.GetHicon()
    $icon = [System.Drawing.Icon]::FromHandle($hIcon)
    $fs = [System.IO.File]::Create($Ico)
    $icon.Save($fs)
    $fs.Close()
    $icon.Dispose()
    $bmp.Dispose()
    Write-Host "Icono creado: $Ico"
}

Ensure-Icon
if (-not (Test-Path -LiteralPath $Bat)) {
    throw "No se encontro: $Bat"
}

$Desktop = [Environment]::GetFolderPath('Desktop')
$LnkPath = Join-Path $Desktop 'AgilDTE - Punto de venta.lnk'

$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($LnkPath)
$sc.TargetPath = $Bat
$sc.WorkingDirectory = $ScriptDir
$sc.WindowStyle = 1
$sc.Description = 'AgilDTE - Punto de venta (impresion silenciosa)'
$sc.IconLocation = "$Ico,0"
$sc.Save()

Write-Host ""
Write-Host "Listo: $LnkPath"
Write-Host "Use ese acceso directo en la caja (no el .bat suelto si quiere el icono)."
Write-Host ""
