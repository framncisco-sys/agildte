# Backup y restauración — AgilDTE + PosAgil

Guía profesional para respaldar **todo lo crítico** y recuperar el sistema ante fallos, errores humanos o cambio de servidor.

---

## 1. Qué debe incluir un backup “completo”

| Componente | Qué es | Prioridad |
|------------|--------|-----------|
| **PostgreSQL** | Empresas, usuarios, productos, ventas, DTE, compras, historial | **Crítico** |
| **Media / archivos** | Logos, PDFs, certificados subidos (`media_volume` en producción) | Alta |
| **Certificados SSL** | `certbot_certs` (Let's Encrypt) | Media (se pueden volver a emitir) |
| **Código** | Repositorio Git (`agildte`) | Media (Git remoto = backup de código) |
| **`.env`** | Contraseñas, claves Django, BD | **Crítico** (copia cifrada aparte, nunca solo en el mismo disco) |

Regla **3-2-1** (recomendada):

- **3** copias de los datos importantes  
- **2** tipos de medio (disco local + nube o otro servidor)  
- **1** copia **fuera** del sitio (oficina / otra región)

---

## 2. Producción AgilDTE (servidor con `docker-compose.prod.yml`)

### Backup automático (ya configurado)

El servicio `backup` ejecuta `scripts/backup.sh` **cada día a las 02:00**:

- **Diarios** → volumen `backup_volume`, carpeta `diario/`, retención **90 días**  
- **Mensuales** (día 1 de cada mes) → `mensual/`, retención **5 años** (1825 días, alineado a conservación tributaria en SV)

Variables en `.env` (raíz `agildte`):

```env
BACKUP_KEEP_DAYS=90
BACKUP_MONTHLY_KEEP_DAYS=1825
```

Opcional: copia mensual a **S3 / DigitalOcean Spaces** con `scripts/backup-upload-s3.sh` (requiere `AWS_ACCESS_KEY_ID`, `S3_BUCKET`, etc.).

### Backup manual (antes de actualizar servidor o migrar)

En el servidor Linux, desde la carpeta del proyecto:

```bash
cd /ruta/a/agildte

# 1) Ejecutar backup ahora
docker compose -f docker-compose.prod.yml exec backup sh /backup.sh

# 2) Listar archivos generados
docker compose -f docker-compose.prod.yml exec backup ls -lh /backups/diario/
docker compose -f docker-compose.prod.yml exec backup ls -lh /backups/mensual/
```

### Copiar backups fuera del servidor (profesional)

```bash
# Ruta típica del volumen Docker en Linux
sudo ls -lh /var/lib/docker/volumes/agildte_backup_volume/_data/diario/

# Copiar el último diario a tu PC o a la nube (ejemplo con scp)
scp usuario@servidor:/var/lib/docker/volumes/agildte_backup_volume/_data/diario/agildte_*.sql.gz ./respaldos/
```

También respalde:

```bash
# Media (facturas, logos, etc.)
docker compose -f docker-compose.prod.yml run --rm -v media_volume:/data alpine \
  tar czf - -C /data . > media_$(date +%Y%m%d).tar.gz

# .env (guardar en gestor de contraseñas o bóveda cifrada)
cp .env respaldos/env_$(date +%Y%m%d).env.enc  # mejor cifrar con su herramienta
```

---

## 3. Desarrollo local — PosAgil (`SistemaPOs`)

Base en Docker: servicio `db`, volumen `posagil_pgdata`, nombre típico `posagil` o `saas_facturacion` (según su `.env`).

### Backup manual (PowerShell en Windows)

```powershell
cd c:\Agildte\agildte\SistemaPOs

# Crear carpeta de respaldos
New-Item -ItemType Directory -Force -Path .\backups | Out-Null

$fecha = Get-Date -Format "yyyyMMdd_HHmmss"
$archivo = ".\backups\posagil_$fecha.sql.gz"

# Dump desde el contenedor Postgres
docker compose exec -T db pg_dump -U postgres -d posagil --encoding=UTF8 | gzip > $archivo

Write-Host "Backup guardado en: $archivo"
```

Ajuste `-U postgres`, `-d posagil` según `AZ_DB_USER` y `AZ_DB_NAME` en su `SistemaPOs\.env`.

### Backup manual (misma carpeta, una línea)

```powershell
docker compose exec -T db pg_dump -U postgres -d posagil | Out-File -Encoding utf8 ".\backups\posagil_manual.sql"
```

Para archivo comprimido en Windows sin `gzip`, use 7-Zip o:

```powershell
docker compose exec db pg_dump -U postgres -d posagil -Fc -f /tmp/posagil.dump
docker compose cp db:/tmp/posagil.dump .\backups\posagil_$(Get-Date -Format yyyyMMdd).dump
```

(`-Fc` = formato custom de PostgreSQL, ideal para restaurar con `pg_restore`.)

---

## 4. Restaurar PostgreSQL

### Producción (AgilDTE)

**Antes de restaurar:**

1. Avisar usuarios / poner mantenimiento.  
2. Opcional: backup del estado actual por si necesita volver atrás.  
3. Detener apps que escriben en la BD:

```bash
docker compose -f docker-compose.prod.yml stop backend frontend nginx posagil
```

**Restaurar** (elija el archivo `.sql.gz` correcto):

```bash
cd /ruta/a/agildte

export POSTGRES_USER=sistema_user
export POSTGRES_PASSWORD=...   # el de .env
export POSTGRES_DB=sistema_contable
export POSTGRES_HOST=db

chmod +x scripts/restore.sh
docker compose -f docker-compose.prod.yml exec -e POSTGRES_USER -e POSTGRES_PASSWORD -e POSTGRES_DB -e POSTGRES_HOST=db backup sh -c "
  apk add --no-cache postgresql-client gzip 2>/dev/null || true
"

# Copiar el backup al contenedor db o montar volumen; forma directa:
gunzip -c /var/lib/docker/volumes/agildte_backup_volume/_data/diario/agildte_sistema_contable_FECHA.sql.gz \
  | docker compose -f docker-compose.prod.yml exec -T db \
    psql -U sistema_user -d sistema_contable
```

Para **reemplazo limpio** (base vacía + importación), use el script:

```bash
docker compose -f docker-compose.prod.yml run --rm \
  -e POSTGRES_HOST=db \
  -e POSTGRES_USER=sistema_user \
  -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -e POSTGRES_DB=sistema_contable \
  -v /var/lib/docker/volumes/agildte_backup_volume/_data:/backups:ro \
  --entrypoint sh backup -c "
    apk add --no-cache postgresql-client gzip
    sh /backup.sh 2>/dev/null || true
  "
# Luego monte restore.sh y ejecute con la ruta del .sql.gz
```

Forma más simple con `scripts/restore.sh` desde un contenedor con acceso a la red `agildte_net`:

```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U sistema_user -d postgres -c \
  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname='sistema_contable' AND pid <> pg_backend_pid();"

docker compose -f docker-compose.prod.yml exec -T db psql -U sistema_user -d postgres -c \
  "DROP DATABASE IF EXISTS sistema_contable; CREATE DATABASE sistema_contable OWNER sistema_user ENCODING 'UTF8';"

gunzip -c /ruta/al/backup.sql.gz \
  | docker compose -f docker-compose.prod.yml exec -T db psql -U sistema_user -d sistema_contable

docker compose -f docker-compose.prod.yml up -d
```

### Local PosAgil (Windows)

```powershell
cd c:\Agildte\agildte\SistemaPOs

# Detener solo la app (dejar db arriba)
docker compose stop posagil

# Recrear base e importar (CUIDADO: borra datos actuales)
docker compose exec -T db psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS posagil;"
docker compose exec -T db psql -U postgres -d postgres -c "CREATE DATABASE posagil OWNER postgres ENCODING 'UTF8';"

# Si el backup es .sql sin comprimir:
Get-Content .\backups\posagil_FECHA.sql | docker compose exec -T db psql -U postgres -d posagil

# Si tiene gzip (Git Bash o WSL):
# gunzip -c backups/posagil_FECHA.sql.gz | docker compose exec -T db psql -U postgres -d posagil

docker compose up -d posagil
```

---

## 5. Restaurar “todo” en servidor nuevo

Checklist ordenado:

1. Instalar Docker + red `agildte_net`: `docker network create agildte_net`  
2. Clonar repo y restaurar `.env` desde bóveda segura  
3. `docker compose -f docker-compose.prod.yml up -d db` → esperar healthy  
4. Restaurar dump PostgreSQL (sección 4)  
5. Restaurar volumen `media` si guardó tarball  
6. `docker compose -f docker-compose.prod.yml up -d` (backend, frontend, nginx, backup)  
7. SSL: `scripts/init-ssl.sh` o renovar certificados  
8. PosAgil: levantar `SistemaPOs` con mismo `AZ_DB_*` apuntando al mismo Postgres  
9. Probar login, una venta de prueba, un DTE de prueba en ambiente de certificación  

---

## 6. Buenas prácticas

| Práctica | Frecuencia |
|---------|------------|
| Backup automático activo (`backup` service Up) | Siempre en producción |
| Backup manual antes de `git pull` + migrate | Cada despliegue importante |
| Copia mensual a nube (S3/Spaces) | Mensual |
| **Prueba de restauración** en entorno de prueba | Trimestral |
| Documentar nombre de BD y usuario en runbook | Una vez |

---

## 7. Archivos del repositorio

| Archivo | Función |
|---------|---------|
| `scripts/backup.sh` | Dump diario + mensual, limpieza por retención |
| `scripts/backup-upload-s3.sh` | Subida opcional a object storage |
| `scripts/restore.sh` | Restauración interactiva (DROP/CREATE + import) |
| `docker-compose.prod.yml` | Servicio `backup` con cron 02:00 |
| `SERVER_UPDATE.md` | Comandos de despliegue y verificación de backups |

---

## 8. Soporte rápido

- **Solo quiero un respaldo hoy (local):** sección 3 (PowerShell).  
- **Servidor en producción:** sección 2 + copiar volumen a disco externo.  
- **Borré datos por error:** sección 4 con el `.sql.gz` **anterior** al error.  
- **Nuevo servidor:** sección 5.

Si la base de PosAgil y la de AgilDTE son la **misma** instancia PostgreSQL, un solo `pg_dump` respalda ambos; si son bases distintas, haga **un dump por cada `POSTGRES_DB` / `AZ_DB_NAME`**.
