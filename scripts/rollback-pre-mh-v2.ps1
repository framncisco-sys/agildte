# Rollback de emergencia a la copia pre-MH-V2
# Uso (desde la raíz del repo Proyecto):
#   powershell -ExecutionPolicy Bypass -File .\scripts\rollback-pre-mh-v2.ps1
#
# Restaura imágenes Docker etiquetadas pre-mh-v2-stable y recrea backend/worker/frontend.
# Opcional: -CheckoutBackupBranch para cambiar el código a backup/pre-mh-v2-20260713

param(
    [switch]$CheckoutBackupBranch,
    [string]$BackupBranch = "backup/pre-mh-v2-20260713",
    [string]$ImageTag = "pre-mh-v2-stable"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "== Rollback pre-MH-V2 ==" -ForegroundColor Cyan
Write-Host "Repo: $Root"

if ($CheckoutBackupBranch) {
    Write-Host "Checkout rama de respaldo: $BackupBranch" -ForegroundColor Yellow
    git fetch origin $BackupBranch 2>$null
    git checkout $BackupBranch
}

$images = @(
    @{ Name = "proyecto-backend"; Service = "backend" },
    @{ Name = "proyecto-facturacion_worker"; Service = "facturacion_worker" },
    @{ Name = "proyecto-frontend"; Service = "frontend" }
)

foreach ($img in $images) {
    $ref = "{0}:{1}" -f $img.Name, $ImageTag
    $exists = docker image inspect $ref 2>$null
    if (-not $exists) {
        throw "No existe la imagen $ref. No se puede hacer rollback Docker."
    }
    Write-Host "Retag $ref -> $($img.Name):latest"
    docker tag $ref "$($img.Name):latest"
}

Write-Host "Recreando contenedores con compose prod + override local..." -ForegroundColor Yellow
docker compose -f docker-compose.prod.yml -f docker-compose.override.local.yml up -d backend facturacion_worker frontend

Start-Sleep -Seconds 8
Write-Host "Estado de contenedores:" -ForegroundColor Cyan
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Image}}" | Select-String -Pattern "proyecto-|NAMES"

Write-Host ""
Write-Host "Rollback aplicado. Verifica emitiendo un CF/CCF de prueba." -ForegroundColor Green
Write-Host "Tag git de referencia: pre-mh-v2-stable | Rama: $BackupBranch"
