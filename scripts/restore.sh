#!/bin/sh
# ─────────────────────────────────────────────────────────────────────────────
# AgilDTE / PostgreSQL — Restaurar backup .sql.gz
#
# Uso (desde la raíz del repo, con stack levantado):
#   ./scripts/restore.sh /ruta/al/backup.sql.gz
#
# Variables (mismas que backup.sh, vía .env o entorno):
#   POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#
# ADVERTENCIA: Sobrescribe la base actual. Detenga tráfico de usuarios antes.
# ─────────────────────────────────────────────────────────────────────────────
set -e

if [ -z "$1" ]; then
  echo "Uso: $0 <archivo.sql.gz|archivo.sql>"
  echo "Ej.: $0 /backups/diario/agildte_sistema_contable_20260603_020001.sql.gz"
  exit 1
fi

BACKUP_FILE="$1"
if [ ! -f "${BACKUP_FILE}" ]; then
  echo "No existe el archivo: ${BACKUP_FILE}"
  exit 1
fi

POSTGRES_HOST="${POSTGRES_HOST:-db}"
POSTGRES_USER="${POSTGRES_USER:?Falta POSTGRES_USER}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:?Falta POSTGRES_PASSWORD}"
POSTGRES_DB="${POSTGRES_DB:?Falta POSTGRES_DB}"

echo "=== Restauración ${POSTGRES_DB} @ ${POSTGRES_HOST} ==="
echo "Archivo: ${BACKUP_FILE}"
echo ""
echo "ATENCIÓN: Se reemplazará el contenido de la base '${POSTGRES_DB}'."
printf "Escriba SI para continuar: "
read -r CONFIRM
if [ "${CONFIRM}" != "SI" ]; then
  echo "Cancelado."
  exit 0
fi

export PGPASSWORD="${POSTGRES_PASSWORD}"

echo "Desconectando sesiones activas..."
psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 <<EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${POSTGRES_DB}' AND pid <> pg_backend_pid();
EOF

echo "Recreando base (DROP + CREATE)..."
psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d postgres -v ON_ERROR_STOP=1 <<EOF
DROP DATABASE IF EXISTS "${POSTGRES_DB}";
CREATE DATABASE "${POSTGRES_DB}" OWNER "${POSTGRES_USER}" ENCODING 'UTF8';
EOF

echo "Importando dump..."
case "${BACKUP_FILE}" in
  *.gz)
    gunzip -c "${BACKUP_FILE}" | psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 -q
    ;;
  *)
    psql -h "${POSTGRES_HOST}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -v ON_ERROR_STOP=1 -q -f "${BACKUP_FILE}"
    ;;
esac

echo "=== Restauración completada ==="
echo "Reinicie backend y POS: docker compose restart backend posagil (según su stack)."
