# AgilDTE — Guía de Despliegue en Producción
**Servidor:** 142.93.77.15 | **Dominio:** agildte.com (Cloudflare)

---

## Changelog — Cambios incluidos en este deploy

### v2.0 — 27 Feb 2026 (deploy actual)

#### Facturación DTE
- **CF (DTE-01) corregido**: `precioUni` y `ventaGravada` ahora van con IVA incluido, como exige MH. `totalGravada`, `montoTotalOperacion` y `totalPagar` reflejan el precio que el usuario ingresó.
- **NIT/DUI cero inicial**: Excel elimina el cero inicial de NITs/DUIs de 8 o 13 dígitos. El sistema ahora los restaura automáticamente (8→9, 13→14 dígitos).
- **JSON descargado con firma y sello**: Al descargar el JSON de una factura aceptada por MH, ahora incluye `firmaElectronica` (JWS) y `selloRecibido`. Nuevo campo `dte_firmado` en el modelo `Venta`.
- **CCF NIT sin padding**: Se eliminó el `zfill(14)` que convertía NITs de 9 dígitos en 14, causando rechazo de MH.

#### Carga Masiva Excel
- Plantilla actualizada con columnas: `nombre_receptor`, `nombre_comercial`, `nit`, `nrc`, `tipo_dte`, `cod_actividad`, `desc_actividad`, `direccion`, `departamento`, `municipio`, `correo`, `telefono`.
- Detección automática NIT/DUI por longitud (9 dígitos = DUI, 14 = NIT).
- Columna `nrc` en lugar de `cliente` para mayor claridad.

#### Historial de Documentos
- **Paginación server-side**: 20 registros por página. Controles de navegación con números de página, botones Anterior/Siguiente e indicador "Mostrando X-Y de N facturas".
- Filtros sincronizan con paginación (al buscar, vuelve a página 1).

#### Seguridad y configuración
- **Login case-insensitive**: `fram`, `FRAM`, `Fram` todos funcionan. La contraseña sigue siendo sensible a mayúsculas.
- **`TIME_ZONE = 'America/El_Salvador'`**: Horas correctas en facturas (antes UTC, ahora UTC-6).
- **`SECURE_PROXY_SSL_HEADER`**: Django sabe que está detrás de nginx HTTPS.
- **`SESSION_COOKIE_SECURE` + `CSRF_COOKIE_SECURE`**: Cookies solo por HTTPS.
- **nginx rate limiting**: `/api/auth/login/` → 10 req/min, `/api/` → 120 req/min, `/admin/` → 20 req/min.
- **nginx `/admin/` restringido por IP**: Solo `127.0.0.1` y `142.93.77.15`. Agregar tu IP si necesitas acceder remotamente.
- **nginx timeouts a 120s**: Igual que gunicorn. Evita 504 en DTEs lentos de MH.
- **Content-Security-Policy**: Cabecera CSP agregada en nginx.
- **`requirements.txt` con versiones fijadas**: Todas las dependencias con `==X.Y.Z` exacto.
- **`.env` y `db.sqlite3` removidos del tracking de git**.

#### Migraciones incluidas
- `0024_add_cliente_nombre_comercial` — campo `nombre_comercial` en modelo `Cliente`
- `0025_add_venta_dte_firmado` — campo `dte_firmado` en modelo `Venta`

---

## Antes de empezar — checklist previo

- [ ] DNS en Cloudflare: `agildte.com` y `www.agildte.com` apuntan a `142.93.77.15`
- [ ] Cloudflare en modo **DNS only** (nube gris) para que certbot llegue directo al servidor
- [ ] Puertos 80 y 443 abiertos en el firewall del servidor (DigitalOcean → Networking → Firewall)
- [ ] `.env` con `POSTGRES_PASSWORD` y `DJANGO_SECRET_KEY` reales (ver paso 2)

---

## 1. Subir el código al servidor

```bash
# En el servidor (conectar por SSH):
ssh root@142.93.77.15
cd /opt/agildte
git pull origin main
```

---

## 2. Configurar el `.env` en el servidor

> **CRÍTICO**: El `.env` NO se sube a git. Debes editarlo manualmente en el servidor.

```bash
nano .env
```

Valores que **debes cambiar** antes de levantar:

```bash
# Generar SECRET_KEY segura (ejecutar en el servidor):
python3 -c "import secrets; print(secrets.token_hex(50))"

# Pegar el resultado en:
DJANGO_SECRET_KEY=<resultado_del_comando>

# Contraseña de PostgreSQL (inventar una fuerte):
POSTGRES_PASSWORD=<contraseña_segura_sin_espacios>
```

El resto del `.env` ya tiene los valores correctos para producción (`DJANGO_DEBUG=False`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, etc.).

---

## 3. Aplicar migraciones y levantar servicios

```bash
# Reconstruir backend (incluye nuevas migraciones y requirements actualizados)
docker compose -f docker-compose.prod.yml up -d --build backend

# Verificar que las migraciones se aplicaron
docker compose -f docker-compose.prod.yml logs backend | grep -E "migrat|OK|ERROR"

# Levantar todos los servicios
docker compose -f docker-compose.prod.yml up -d

# Verificar estado
docker compose -f docker-compose.prod.yml ps
# Esperado: db, backend, frontend, nginx, backup → todos "Up"
```

---

## 4. Primera puesta en marcha — obtener SSL (solo si es deploy nuevo)

```bash
chmod +x scripts/init-ssl.sh scripts/renew-ssl.sh scripts/backup.sh
./scripts/init-ssl.sh
```

> **Si ya tienes SSL y solo actualizas el código**, salta este paso. Solo haz `git pull` + `docker compose up -d --build`.

---

## 5. Verificar que todo funciona

```bash
# HTTPS responde
curl -I https://agildte.com
# Esperado: HTTP/2 200

# HTTP redirige a HTTPS
curl -I http://agildte.com
# Esperado: 301 → https://agildte.com/

# API responde
curl https://agildte.com/api/auth/login/ -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"fram","password":"TU_PASSWORD"}'
# Esperado: {"access":"...","refresh":"..."}

# Migraciones aplicadas
docker compose -f docker-compose.prod.yml exec backend \
  python manage.py showmigrations api | tail -5
# Esperado: [X] 0024_add_cliente_nombre_comercial
#           [X] 0025_add_venta_dte_firmado
```

---

## 6. Verificar nginx — rate limiting y admin

```bash
# Cabeceras de seguridad (debe mostrar CSP, HSTS, X-Frame-Options)
curl -I https://agildte.com/api/ 2>/dev/null | grep -E "strict|frame|content-security|x-content"

# Admin solo accesible desde el servidor (debe dar 403 desde fuera)
# Si necesitas acceder al admin desde tu IP, editar nginx/nginx.conf:
#   allow TU_IP_PUBLICA;   ← agregar antes del "deny all;" en /admin/
# Luego recargar nginx:
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

---

## 7. Verificar backups

```bash
# Ejecutar backup manual para probar
docker compose -f docker-compose.prod.yml exec backup /backup.sh

# Ver archivos generados
docker compose -f docker-compose.prod.yml exec backup ls -lh /backups/
```

---

## 8. Renovación automática de SSL

```bash
# Verificar cron configurado
crontab -l
# Debe mostrar: 0 3 * * * ... bash scripts/renew-ssl.sh

# Renovar manualmente (para probar)
./scripts/renew-ssl.sh
```

---

## Comandos útiles de mantenimiento

```bash
# Ver logs en tiempo real
docker compose -f docker-compose.prod.yml logs -f

# Reiniciar solo el backend (después de cambios en código)
docker compose -f docker-compose.prod.yml restart backend

# Actualizar código y reconstruir
git pull && docker compose -f docker-compose.prod.yml up -d --build

# Ver espacio en disco
docker system df -v

# Restaurar un backup
gunzip -c /var/lib/docker/volumes/agildte_backup_volume/_data/agildte_sistema_contable_YYYYMMDD_HHMMSS.sql.gz \
  | docker compose -f docker-compose.prod.yml exec -T db \
    psql -U sistema_user -d sistema_contable

# Recargar nginx sin cortar conexiones (después de editar nginx.conf)
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
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

---

## Si necesitas acceder al /admin/ desde tu IP

Edita `nginx/nginx.conf`, bloque `/admin/`, y agrega tu IP antes del `deny all;`:

```nginx
allow 127.0.0.1;
allow 142.93.77.15;
allow TU_IP_PUBLICA;   # ← agregar aquí
deny  all;
```

Luego recarga nginx:
```bash
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```
