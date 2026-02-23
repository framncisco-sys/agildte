#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# AgilDTE — Sube backups mensuales a S3 / DigitalOcean Spaces
#
# Se ejecuta después del backup mensual (ej. desde backup.sh o cron).
# Requiere: aws-cli instalado (apt-get install awscli / pip install awscli)
#
# Variables de entorno (.env o export):
#   AWS_ACCESS_KEY_ID
#   AWS_SECRET_ACCESS_KEY
#   S3_BUCKET           (ej: agildte-backups)
#   S3_REGION           (ej: us-east-1 o nyc3 para DO Spaces)
#   S3_ENDPOINT         (opcional, para DO Spaces: https://nyc3.digitaloceanspaces.com)
#   BACKUP_MONTHLY_DIR  (default: /backups/mensual)
#   S3_PREFIX           (opcional, ej: backups/empresa1)
#
# Uso:
#   ./scripts/backup-upload-s3.sh
#   # O integrado en backup.sh:
#   if [ "${DIA}" = "01" ]; then
#     ... do_backup ...
#     [ -x ./scripts/backup-upload-s3.sh ] && ./scripts/backup-upload-s3.sh
#   fi
# ─────────────────────────────────────────────────────────────────────────────
set -e

MONTHLY_DIR="${BACKUP_MONTHLY_DIR:-/backups/mensual}"
S3_BUCKET="${S3_BUCKET}"
S3_REGION="${S3_REGION:-us-east-1}"
S3_ENDPOINT="${S3_ENDPOINT}"
S3_PREFIX="${S3_PREFIX:-backups}"

if [ -z "${AWS_ACCESS_KEY_ID}" ] || [ -z "${AWS_SECRET_ACCESS_KEY}" ] || [ -z "${S3_BUCKET}" ]; then
  echo "[$(date)] backup-upload-s3: Saltando (faltan AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY o S3_BUCKET)"
  exit 0
fi

if [ ! -d "${MONTHLY_DIR}" ]; then
  echo "[$(date)] backup-upload-s3: No existe ${MONTHLY_DIR}"
  exit 0
fi

# Configurar endpoint para DigitalOcean Spaces
EXTRA_ARGS=""
if [ -n "${S3_ENDPOINT}" ]; then
  EXTRA_ARGS="--endpoint-url ${S3_ENDPOINT}"
fi

echo "=== [$(date)] Subiendo backups mensuales a S3/Spaces ==="

count=0
for f in "${MONTHLY_DIR}"/agildte_*.sql.gz; do
  [ -f "$f" ] || continue
  name=$(basename "$f")
  s3_path="${S3_PREFIX}/${name}"
  echo "  Subiendo: $name -> s3://${S3_BUCKET}/${s3_path}"
  if aws s3 cp "$f" "s3://${S3_BUCKET}/${s3_path}" ${EXTRA_ARGS} --region "${S3_REGION}" 2>/dev/null; then
    count=$((count + 1))
  else
    echo "  ERROR subiendo $name"
  fi
done

echo "  Subidos: ${count} archivos"
echo "=== [$(date)] Completado ==="
