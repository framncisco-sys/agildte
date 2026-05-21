# Pantalla de inicio AgilDTE al abrir el POS desde el .bat (Windows).
param(
    [Parameter(Mandatory = $true)][string]$LogoPath,
    [int]$Seconds = 2
)

$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = 'AgilDTE — Punto de venta'
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedDialog
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.Color]::White
$form.ClientSize = New-Object System.Drawing.Size(560, 300)

$panel = New-Object System.Windows.Forms.Panel
$panel.Dock = [System.Windows.Forms.DockStyle]::Fill
$panel.BackColor = [System.Drawing.Color]::White
$form.Controls.Add($panel)

$pic = New-Object System.Windows.Forms.PictureBox
$pic.Dock = [System.Windows.Forms.DockStyle]::Fill
$pic.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::Zoom
$pic.BackColor = [System.Drawing.Color]::White
if (Test-Path -LiteralPath $LogoPath) {
    $img = [System.Drawing.Image]::FromFile((Resolve-Path -LiteralPath $LogoPath))
    $pic.Image = $img
}
$panel.Controls.Add($pic)

$lbl = New-Object System.Windows.Forms.Label
$lbl.Text = 'Abriendo punto de venta...'
$lbl.Dock = [System.Windows.Forms.DockStyle]::Bottom
$lbl.Height = 40
$lbl.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$lbl.Font = New-Object System.Drawing.Font('Segoe UI', 10)
$lbl.ForeColor = [System.Drawing.Color]::FromArgb(30, 64, 120)
$form.Controls.Add($lbl)

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = [Math]::Max(800, $Seconds * 1000)
$timer.Add_Tick({
    $timer.Stop()
    if ($pic.Image) { $pic.Image.Dispose() }
    $form.Close()
})
$form.Add_Shown({ $form.Activate(); $timer.Start() })
[void][System.Windows.Forms.Application]::Run($form)
