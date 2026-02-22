#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# AgilDTE — Inicialización SSL con Let's Encrypt (Certbot)
# Ejecutar UNA SOLA VEZ en el servidor cuando el dominio ya apunta a la IP.
#
# Uso:
#   chmod +x scripts/init-ssl.sh
#   ./scripts/init-ssl.sh
#
# Requisitos previos:
#   - DNS de agildte.com ya apunta a 142.93.77.15 (verificar con: nslookup agildte.com)
#   - Puertos 80 y 443 abiertos en el firewall del servidor
#   - .env con POSTGRES_PASSWORD y DJANGO_SECRET_KEY configurados
# ─────────────────────────────────────────────────────────────────────────────
set -e

DOMAIN="agildte.com"
EMAIL="admin@agildte.com"   # <-- cambia esto por tu email real antes de ejecutar
COMPOSE="docker compose -f docker-compose.prod.yml"

echo "======================================================"
echo " AgilDTE — Inicialización SSL para ${DOMAIN}"
echo "======================================================"

# ─── Paso 1: Verificar que el DNS ya resuelve ─────────────────────────────
echo ""
echo "[1/6] Verificando resolución DNS de ${DOMAIN}..."
RESOLVED=$(dig +short "${DOMAIN}" 2>/dev/null || nslookup "${DOMAIN}" 2>/dev/null | grep Address | tail -1 | awk '{print $2}')
if [ -z "${RESOLVED}" ]; then
    echo "  ERROR: No se pudo resolver ${DOMAIN}."
    echo "  Asegúrate de que Cloudflare apunte a 142.93.77.15 y espera la propagación."
    exit 1
fi
echo "  OK: ${DOMAIN} → ${RESOLVED}"

# ─── Paso 2: Arrancar con nginx HTTP (sin SSL) para validación ACME ───────
echo ""
echo "[2/6] Activando nginx en modo HTTP inicial (sin SSL)..."
cp nginx/nginx-init.conf nginx/nginx.conf.bak 2>/dev/null || true
cp nginx/nginx-init.conf /tmp/nginx-init-active.conf

# Arrancar todos los servicios con config HTTP temporal
${COMPOSE} down --remove-orphans 2>/dev/null || true

# Montar temporalmente nginx-init.conf en lugar de nginx.conf
docker run -d --name nginx-init-temp \
    --network "$(basename $(pwd))_default" \
    -p 80:80 \
    -v "$(pwd)/nginx/nginx-init.conf:/etc/nginx/nginx.conf:ro" \
    -v "$(docker volume ls -q | grep certbot_www || echo certbot_www):/var/www/certbot" \
    nginx:alpine 2>/dev/null || true

# Levantar solo los servicios necesarios para que nginx-init apunte a ellos
${COMPOSE} up -d db backend frontend 2>&1

sleep 5

# Levantar nginx con la config HTTP inicial
docker stop nginx-init-temp 2>/dev/null || true
docker rm nginx-init-temp 2>/dev/null || true

# Reemplazar temporalmente nginx.conf con la versión HTTP
cp nginx/nginx.conf nginx/nginx.conf.https.bak
cp nginx/nginx-init.conf nginx/nginx.conf

${COMPOSE} up -d nginx 2>&1
echo "  OK: nginx corriendo en HTTP para validación ACME"

sleep 3

# ─── Paso 3: Obtener certificado con certbot ──────────────────────────────
echo ""
echo "[3/6] Obteniendo certificado SSL de Let's Encrypt..."
${COMPOSE} --profile certbot run --rm certbot certonly \
    --webroot \
    --webroot-path /var/www/certbot \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}" \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    --force-renewal

echo "  OK: Certificado obtenido en /etc/letsencrypt/live/${DOMAIN}/"

# ─── Paso 4: Activar nginx con HTTPS ─────────────────────────────────────
echo ""
echo "[4/6] Activando nginx con HTTPS..."
cp nginx/nginx.conf.https.bak nginx/nginx.conf

${COMPOSE} restart nginx
sleep 3
echo "  OK: nginx corriendo con HTTPS"

# ─── Paso 5: Verificar HTTPS ─────────────────────────────────────────────
echo ""
echo "[5/6] Verificando HTTPS..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://${DOMAIN}/api/health/" 2>/dev/null || echo "000")
if [ "${HTTP_CODE}" = "200" ] || [ "${HTTP_CODE}" = "401" ] || [ "${HTTP_CODE}" = "404" ]; then
    echo "  OK: HTTPS responde con código ${HTTP_CODE}"
else
    echo "  ADVERTENCIA: HTTPS devolvió código ${HTTP_CODE}. Revisa los logs con:"
    echo "    ${COMPOSE} logs nginx"
fi

# ─── Paso 6: Configurar renovación automática ─────────────────────────────
echo ""
echo "[6/6] Configurando renovación automática de certificado..."
chmod +x scripts/renew-ssl.sh
CRON_JOB="0 3 * * * cd $(pwd) && bash scripts/renew-ssl.sh >> /var/log/agildte-renew.log 2>&1"
(crontab -l 2>/dev/null | grep -v "renew-ssl"; echo "${CRON_JOB}") | crontab -
echo "  OK: Cron configurado para renovar cada día a las 03:00 AM"

echo ""
echo "======================================================"
echo " SSL ACTIVADO CORRECTAMENTE"
echo " Accede a: https://${DOMAIN}"
echo " Admin:    https://${DOMAIN}/admin/"
echo "======================================================"
