#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# AgilDTE — Backup diario de PostgreSQL
# Se ejecuta a las 02:00 AM via cron dentro del contenedor 'backup'.
#
# Variables de entorno requeridas (leídas desde .env via docker-compose):
#   POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_HOST
#   BACKUP_KEEP_DAYS  (días a conservar, default 30)
# ─────────────────────────────────────────────────────────────────────────────
set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="${BACKUP_DIR}/agildte_${POSTGRES_DB}_${TIMESTAMP}.sql.gz"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"

echo "=== [$(date)] Iniciando backup de ${POSTGRES_DB} ==="

# Crear directorio si no existe
mkdir -p "${BACKUP_DIR}"

# Dump comprimido con gzip
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST:-db}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --no-password \
    --format=plain \
    --encoding=UTF8 \
    | gzip > "${FILENAME}"

SIZE=$(du -sh "${FILENAME}" | cut -f1)
echo "  Backup creado: ${FILENAME} (${SIZE})"

# Eliminar backups más antiguos que KEEP_DAYS días
echo "  Eliminando backups anteriores a ${KEEP_DAYS} días..."
find "${BACKUP_DIR}" -name "agildte_*.sql.gz" -mtime "+${KEEP_DAYS}" -delete
REMAINING=$(find "${BACKUP_DIR}" -name "agildte_*.sql.gz" | wc -l)
echo "  Backups conservados: ${REMAINING}"

echo "=== [$(date)] Backup completado ==="
