#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# AgilDTE — Backup PostgreSQL con retención legal (5 años para facturas)
#
# Estrategia por capas (sin saturar disco):
#   1. DIARIO: backup cada día a las 02:00, retención 90 días (recuperación reciente)
#   2. MENSUAL: backup el día 1 de cada mes, retención 5 años (ley tributaria SV)
#
# Variables .env:
#   BACKUP_KEEP_DAYS=90         (diarios)
#   BACKUP_MONTHLY_KEEP_DAYS=1825   (mensuales, 5 años)
# ─────────────────────────────────────────────────────────────────────────────
set -e

BACKUP_DIR="/backups"
DAILY_DIR="${BACKUP_DIR}/diario"
MONTHLY_DIR="${BACKUP_DIR}/mensual"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
KEEP_DAYS="${BACKUP_KEEP_DAYS:-90}"
KEEP_MONTHLY_DAYS="${BACKUP_MONTHLY_KEEP_DAYS:-1825}"   # 5 años

mkdir -p "${DAILY_DIR}" "${MONTHLY_DIR}"

# Función: crear backup
do_backup() {
    local dest="$1"
    PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
        -h "${POSTGRES_HOST:-db}" \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --no-password \
        --format=plain \
        --encoding=UTF8 \
        | gzip > "${dest}"
}

echo "=== [$(date)] Backup ${POSTGRES_DB} ==="

# ─── 1. Backup diario (siempre) ─────────────────────────────────────────────
FILENAME="${DAILY_DIR}/agildte_${POSTGRES_DB}_${TIMESTAMP}.sql.gz"
do_backup "${FILENAME}"
echo "  Diario: ${FILENAME} ($(du -sh "${FILENAME}" | cut -f1))"

# Limpiar diarios antiguos
find "${DAILY_DIR}" -name "agildte_*.sql.gz" -mtime "+${KEEP_DAYS}" -delete

# ─── 2. Backup mensual (solo día 1 del mes) ─────────────────────────────────
DIA=$(date +%d)
if [ "${DIA}" = "01" ]; then
    MES=$(date +%Y%m)
    MONTHLY_FILE="${MONTHLY_DIR}/agildte_${POSTGRES_DB}_${MES}_01.sql.gz"
    do_backup "${MONTHLY_FILE}"
    echo "  Mensual: ${MONTHLY_FILE} ($(du -sh "${MONTHLY_FILE}" | cut -f1))"
    # Subir a S3/Spaces si está configurado (variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET)
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if [ -x "${SCRIPT_DIR}/backup-upload-s3.sh" ]; then
        "${SCRIPT_DIR}/backup-upload-s3.sh" || true
    fi
fi

# Limpiar mensuales con más de 5 años
find "${MONTHLY_DIR}" -name "agildte_*.sql.gz" -mtime "+${KEEP_MONTHLY_DAYS}" -delete

REMAINING_DAILY=$(find "${DAILY_DIR}" -name "agildte_*.sql.gz" | wc -l)
REMAINING_MONTHLY=$(find "${MONTHLY_DIR}" -name "agildte_*.sql.gz" | wc -l)
echo "  Conservados: ${REMAINING_DAILY} diarios, ${REMAINING_MONTHLY} mensuales"
echo "=== [$(date)] Completado ==="
