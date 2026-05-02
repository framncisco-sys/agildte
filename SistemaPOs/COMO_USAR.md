# Cómo usar AZ DIGITAL

## 1. Iniciar el sistema web

```bash
python app.py
```

Luego abra en el navegador: **http://127.0.0.1:8000**

---

## 2. Verificar que todo esté bien

```bash
python scripts/verificar_sistema.py
```

Este script revisa: base de datos, usuarios admin, empresas, y que la app responda.

---

## 3. Si es SUPERUSUARIO

1. Inicie sesión con su usuario (ej: `admin`).
2. Verá una lista de empresas → **haga clic en "Entrar"** en la empresa que quiere gestionar.
3. Después podrá usar: Configuración, Clientes, Inventario, Usuarios, Sucursales.

**Importante:** Debe seleccionar una empresa antes de ver Configuración, Inventario, etc.

---

## 4. Si algo no funciona

- **Error de base de datos:** Revise que exista el archivo `.env` con:
  ```
  AZ_DB_NAME=saas_facturacion
  AZ_DB_USER=postgres
  AZ_DB_PASSWORD=su_contraseña
  AZ_DB_HOST=127.0.0.1
  AZ_DB_PORT=5432
  ```

- **Error 500:** Mire el archivo `server.log` para ver el detalle.

- **No hay superusuario:** Ejecute:
  ```bash
  python scripts/configurar_admin_unico.py
  ```

---

## Archivos importantes

| Archivo | Uso |
|---------|-----|
| `app.py` | **Aplicación web** (Flask) - use este |
| `main.py` | Aplicación de escritorio (Tkinter) para cargar productos con escáner |
