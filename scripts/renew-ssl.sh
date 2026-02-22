#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# AgilDTE — Renovación automática de certificado SSL
# Ejecutado por cron cada día a las 03:00 AM (configurado por init-ssl.sh).
# Certbot solo renueva si el cert expira en menos de 30 días.
# ─────────────────────────────────────────────────────────────────────────────
set -e

COMPOSE_FILE="$(dirname "$0")/../docker-compose.prod.yml"
COMPOSE="docker compose -f ${COMPOSE_FILE}"

echo "=== [$(date)] Inicio renovación SSL ==="

# Intentar renovación
${COMPOSE} --profile certbot run --rm certbot renew --quiet

# Si certbot renovó el cert, reiniciar nginx para que lo cargue
if [ $? -eq 0 ]; then
    echo "  Recargando nginx..."
    ${COMPOSE} exec nginx nginx -s reload
    echo "  OK: nginx recargado con el nuevo certificado"
fi

echo "=== [$(date)] Renovación SSL completada ==="
