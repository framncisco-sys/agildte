# Actualizar el servidor (agildte-prod)

Cuando `git pull` falle por cambios locales o por `.env`, ejecuta estos pasos **en el servidor** (SSH).

---

## Actualizar sin afectar la base de datos de los usuarios

La base de datos está en el volumen Docker `postgres_data`. Al actualizar código (git pull + build + up) **los datos no se borran**. Las migraciones que se ejecutan al arrancar el backend solo **añaden** tablas o columnas con valores por defecto; no eliminan datos de usuarios.

### Opción recomendada: respaldo rápido antes de actualizar

En el servidor (SSH), **antes** de hacer `git pull` y `up`:

```bash
cd ~/agildte
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U sistema_user sistema_contable > backup_$(date +%Y%m%d_%H%M).sql
```

Eso deja un archivo `backup_YYYYMMDD_HHMM.sql` en `~/agildte`. Si algo fallara, podrías restaurar con:

```bash
docker compose -f docker-compose.prod.yml exec -T db psql -U sistema_user sistema_contable < backup_YYYYMMDD_HHMM.sql
```

### Pasos para actualizar (sin tocar datos)

**1. En tu PC:** subir cambios al repo (si aplica).

```bash
git add .
git commit -m "Actualización"
git push origin main
```

**2. En el servidor (SSH):**

```bash
cd ~/agildte
# Opcional: respaldo de .env por si Git lo pisa
cp .env .env.backup

# Si Git se queja por .env, quítalo del camino y restáuralo después
mv .env .env.mio 2>/dev/null || true
git pull origin main
mv .env.mio .env 2>/dev/null || true

# Reconstruir y levantar (la BD sigue en el volumen; migrate solo aplica cambios nuevos)
docker compose -f docker-compose.prod.yml build --no-cache backend frontend
docker compose -f docker-compose.prod.yml up -d
```

Al arrancar, el backend ejecuta `migrate --noinput` y aplica solo las migraciones pendientes (por ejemplo, nueva columna `tipo_impuesto` en Producto). Los datos existentes se mantienen.

---

## Solución inmediata (error del firmador "denied")

Si al hacer `docker compose up -d --build` falla por la imagen del firmador, **levanta solo los otros servicios** (sin el firmador). En el servidor:

```bash
cd ~/agildte
docker compose -f docker-compose.prod.yml up -d --build db backend frontend nginx
```

Así se levantan **db, backend, frontend y nginx**; el firmador no se inicia y no se intenta descargar su imagen. La app funcionará; solo la firma de DTE fallará hasta que tengas una imagen de firmador válida.

(Opcional) Para que en el futuro `docker compose up -d --build` no intente el firmador, edita el compose en el servidor:

```bash
nano docker-compose.prod.yml
```

- En el servicio `firmador`, cambia la línea `image:` a: `image: ${FIRMADOR_IMAGE:-busybox:latest}`
- Justo debajo de `firmador:`, añade (con la misma indentación que el resto del servicio):
  ```yaml
    profiles:
      - firmador
  ```
Guarda (Ctrl+O, Enter, Ctrl+X). Después de eso, `docker compose up -d --build` ya no intentará el firmador.

---

## Firmador opcional (cuando el repo esté actualizado)

El servicio **firmador** no se inicia por defecto (las imágenes públicas probadas están denegadas). El resto del stack (db, backend, frontend, nginx) arranca sin él. La firma de DTE fallará hasta que tengas una imagen de firmador válida; entonces en `.env` defines `FIRMADOR_IMAGE=tu-imagen` y levantas con:

```bash
docker compose -f docker-compose.prod.yml --profile firmador up -d
```

## Comando rápido (copiar y pegar en el servidor)

```bash
cd ~/agildte
cp .env .env.backup
sed -i '/FIRMADOR_IMAGE/d' .env
grep -q 'FIRMADOR_URL' .env || echo 'FIRMADOR_URL=http://firmador:8113/' >> .env
git checkout -- docker-compose.prod.yml
test -f .env && mv .env .env.mio
git pull origin main
test -f .env.mio && mv .env.mio .env
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --build
```

Si `git pull` sigue fallando por `.env`, ejecuta a mano: `mv .env .env.mio`, luego `git pull origin main`, luego `mv .env.mio .env`.

---

## 1. Guardar tu `.env` actual (tiene las contraseñas reales)

```bash
cd ~/agildte
cp .env .env.backup
```

## 2. Quitar la imagen antigua del firmador del `.env`

```bash
sed -i '/FIRMADOR_IMAGE/d' .env
```

(O edita a mano: `nano .env` y borra la línea que diga `FIRMADOR_IMAGE=nitram19/firmador-sv`.)

## 3. Permitir el pull: descartar cambios locales del compose y no sobrescribir `.env`

```bash
# Descarta cambios locales en docker-compose.prod.yml (se reemplazará con el del repo)
git checkout -- docker-compose.prod.yml

# Si Git dice que .env sería sobrescrito, quita .env del índice y mantén tu copia
git update-index --assume-unchanged .env 2>/dev/null || true
git pull origin main
```

Si aun así Git reclama por `.env`:

```bash
# Guardar .env, quitar del árbol, hacer pull, restaurar .env
mv .env .env.mio
git pull origin main
mv .env.mio .env
```

## 4. Asegurar que `.env` no tenga la imagen que falla

```bash
grep -q 'FIRMADOR_IMAGE=nitram19' .env && sed -i '/FIRMADOR_IMAGE=nitram19/d' .env || true
```

Añade la URL del firmador si no está:

```bash
grep -q 'FIRMADOR_URL' .env || echo 'FIRMADOR_URL=http://firmador:8113/' >> .env
```

## 5. Levantar de nuevo

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

**Resumen:** El error de "pull access denied for nitram19/firmador-sv" se debe a que en el servidor seguías con el compose y el `.env` viejos. Después de `git pull` (con los pasos de arriba) y de quitar `FIRMADOR_IMAGE=nitram19/firmador-sv` del `.env`, el compose usará por defecto `ghcr.io/rhernandez-sv/firmador-libre:latest`.
