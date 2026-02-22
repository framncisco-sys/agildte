# AgilDTE — Guía de Despliegue en Producción
**Servidor:** 142.93.77.15 | **Dominio:** agildte.com (Cloudflare)

---

## Antes de empezar — checklist previo

- [ ] DNS en Cloudflare: `agildte.com` y `www.agildte.com` apuntan a `142.93.77.15`
- [ ] Cloudflare en modo **DNS only** (nube gris, no naranja) para que certbot llegue directo al servidor
- [ ] Puertos 80 y 443 abiertos en el firewall del servidor (DigitalOcean → Networking → Firewall)
- [ ] `.env` con `POSTGRES_PASSWORD` y `DJANGO_SECRET_KEY` reales (no los de ejemplo)

---

## 1. Subir el código al servidor

```bash
# Desde tu máquina local:
git add -A && git commit -m "Día 3: HTTPS, gzip, backup, dominio producción"
git push origin main

# En el servidor (conectar por SSH):
ssh root@142.93.77.15
cd /opt/agildte          # o la ruta donde está el proyecto
git pull origin main
```

---

## 2. Configurar el `.env` en el servidor

```bash
# Editar .env (ya tiene los valores correctos de agildte.com, solo falta la contraseña y secret key)
nano .env

# Valores críticos que DEBES cambiar:
#   POSTGRES_PASSWORD=una_contraseña_muy_segura
#   DJANGO_SECRET_KEY=genera_con:  python3 -c "import secrets; print(secrets.token_hex(50))"
```

---

## 3. Primera puesta en marcha — obtener SSL

Este script hace todo automáticamente:
1. Arranca la app en HTTP temporal
2. Pide el certificado a Let's Encrypt
3. Activa nginx con HTTPS
4. Configura el cron de renovación

```bash
chmod +x scripts/init-ssl.sh scripts/renew-ssl.sh scripts/backup.sh
./scripts/init-ssl.sh
```

> **Si ya tienes los servicios corriendo y solo quieres el certificado** (sin reiniciar todo):
>
> ```bash
> # 1. Cambia nginx a modo HTTP temporal
> cp nginx/nginx.conf nginx/nginx.conf.https.bak
> cp nginx/nginx-init.conf nginx/nginx.conf
> docker compose -f docker-compose.prod.yml restart nginx
>
> # 2. Obtener certificado
> docker compose -f docker-compose.prod.yml --profile certbot run --rm certbot certonly \
>   --webroot -w /var/www/certbot \
>   -d agildte.com -d www.agildte.com \
>   --email admin@agildte.com \
>   --agree-tos --no-eff-email
>
> # 3. Restaurar nginx con HTTPS
> cp nginx/nginx.conf.https.bak nginx/nginx.conf
> docker compose -f docker-compose.prod.yml restart nginx
> ```

---

## 4. Levantar todos los servicios

```bash
docker compose -f docker-compose.prod.yml up -d
```

Verificar que todo está corriendo:

```bash
docker compose -f docker-compose.prod.yml ps
# Esperado: db, backend, frontend, nginx, backup → todos "Up"
```

---

## 5. Verificar HTTPS

```bash
curl -I https://agildte.com
# Esperado: HTTP/2 200 (o 301 si redirige a /login)

curl -I http://agildte.com
# Esperado: HTTP/1.1 301 → https://agildte.com/
```

---

## 6. Verificar backups

```bash
# Ver logs del contenedor de backup
docker compose -f docker-compose.prod.yml logs backup

# Ejecutar backup manual para probar
docker compose -f docker-compose.prod.yml exec backup /backup.sh

# Ver los archivos generados
docker compose -f docker-compose.prod.yml exec backup ls -lh /backups/
```

---

## 7. Renovación automática de SSL

El cron se configura automáticamente con `init-ssl.sh`. Para verificarlo:

```bash
crontab -l
# Debe mostrar: 0 3 * * * ... bash scripts/renew-ssl.sh
```

Para renovar manualmente (también sirve para probar):

```bash
./scripts/renew-ssl.sh
```

---

## Comandos útiles de mantenimiento

```bash
# Ver logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f

# Reiniciar solo el backend (después de cambios en código)
docker compose -f docker-compose.prod.yml restart backend

# Actualizar imagen y reiniciar
git pull && docker compose -f docker-compose.prod.yml up -d --build backend

# Ver espacio en disco usado por volúmenes
docker system df -v

# Restaurar un backup
gunzip -c /var/lib/docker/volumes/agildte_backup_volume/_data/agildte_sistema_contable_YYYYMMDD_HHMMSS.sql.gz \
  | docker compose -f docker-compose.prod.yml exec -T db \
    psql -U sistema_user -d sistema_contable
```

---

## Cloudflare — configuración recomendada

| Ajuste | Valor |
|--------|-------|
| SSL/TLS mode | **Full (strict)** — después de activar el cert |
| Always Use HTTPS | Activado |
| HTTP/3 (QUIC) | Activado |
| Rocket Loader | **Desactivado** (puede interferir con React) |
| Caching → Browser TTL | 4 horas |

> Durante la validación de certbot, usa **DNS only** (nube gris). Después de obtener el cert, puedes activar el proxy (nube naranja) para Cloudflare WAF y CDN.
