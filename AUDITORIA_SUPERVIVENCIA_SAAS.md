# Auditoría crítica – Modo Supervivencia SaaS
## Facturación DTE El Salvador (Django/React)

Enfoque: **Lean Startup + Riesgo Legal**. Sin teoría, solo lógica de código y decisiones ejecutables.

---

## 1. Filtro multi-tenant: cómo implementarlo (código)

Ya existe el módulo **`api/utils/tenant.py`** con esta lógica:

- **`get_empresa_ids_allowlist(request)`**  
  Devuelve la lista de `empresa_id` a los que el usuario puede acceder:
  - No autenticado → `[]`
  - Superuser → todos los IDs
  - PerfilUsuario con `empresa=None` (MASTER) → todos los IDs
  - PerfilUsuario con `empresa=X` → `[X]`

- **`require_empresa_allowed(request, empresa_id)`**  
  Si `empresa_id` no está en la allowlist → devuelve `Response(403)`. Si está bien → devuelve `None`.

- **`require_object_empresa_allowed(request, obj)`**  
  Para recursos por PK (venta, compra, etc.): si `obj.empresa_id` no está permitido → `Response(404)`. Si está bien → `None`.

### Dónde usarlo en las vistas

**Patrón A – Listas que filtran por `empresa_id` (query params o body)**  
Al inicio de la vista:

1. `empresa_ids = get_empresa_ids_allowlist(request)`  
2. Si la ruta es privada y `not empresa_ids` → `return Response({"error": "No autorizado"}, status=401)`.  
3. Obtener `empresa_id` de `request.query_params` o `request.data`.  
4. Si el endpoint **exige** `empresa_id`: `r = require_empresa_allowed(request, empresa_id)`; si `r is not None`: `return r`.  
5. Construir el queryset **siempre** restringido:  
   `queryset = Modelo.objects.filter(empresa_id__in=empresa_ids)`  
   Si además el cliente envió un `empresa_id` válido, opcionalmente:  
   `if empresa_id: queryset = queryset.filter(empresa_id=int(empresa_id))`.

**Patrón B – Detalle por PK (obtener_venta, obtener_compra, generar_pdf, etc.)**  
Después de hacer `obj = Modelo.objects.get(pk=pk)`:

1. `r = require_object_empresa_allowed(request, obj)`  
2. Si `r is not None`: `return r`  
3. Seguir con la lógica normal.

**Patrón C – Acciones con `empresa_id` en el body (ej. procesar_json_dte)**  
Al inicio:

1. `empresa_id = request.data.get('empresa_id')`  
2. `r = require_empresa_allowed(request, empresa_id)`; si `r is not None`: `return r`  
3. Luego sí hacer `Empresa.objects.get(id=empresa_id)`.

### Ejemplo concreto: `listar_ventas`

Al inicio de `listar_ventas` (después de los imports y antes de usar `empresa_id`):

```python
from .utils.tenant import get_empresa_ids_allowlist, require_empresa_allowed

# Dentro de listar_ventas, PRIMERO:
empresa_ids = get_empresa_ids_allowlist(request)
if not empresa_ids:
    return Response({"error": "Autenticación requerida"}, status=401)
empresa_id = request.query_params.get('empresa_id')
if empresa_id:
    r = require_empresa_allowed(request, empresa_id)
    if r is not None:
        return r
# Sustituir la construcción del queryset por:
ventas = Venta.objects.select_related('empresa', 'cliente').filter(empresa_id__in=empresa_ids)
if empresa_id:
    ventas = ventas.filter(empresa_id=int(empresa_id))
# ... resto de filtros (periodo, tipo, etc.) sobre ventas
```

### Ejemplo: `obtener_venta`

Después de `venta = Venta.objects.get(pk=pk)`:

```python
from .utils.tenant import require_object_empresa_allowed

# Dentro de obtener_venta, después del get:
r = require_object_empresa_allowed(request, venta)
if r is not None:
    return r
```

### Lista de vistas a tocar (mínimo para cerrar fugas)

- **Listas / reportes que usan `empresa_id`:**  
  listar_ventas, listar_compras, listar_productos, listar_liquidaciones, listar_retenciones_recibidas, procesar_json_dte, generar_csv_161/162/163, reporte_*_empresa, vista_previa_*, obtener_ventas_para_conciliacion, download_batch_ventas (si usa empresa_id), resumen_fiscal.
- **Detalle por PK:**  
  obtener_venta, obtener_compra, borrar_compra, actualizar_compra, borrar_venta, actualizar_venta, generar_pdf_venta_endpoint, generar_dte_venta, emitir_factura (ViewSet), invalidar (ViewSet), obtener_retencion_recibida, aplicar_retencion.
- **Crear:**  
  crear_venta, crear_venta_con_detalles, crear_compra: validar que `empresa_id` del body esté en allowlist antes de guardar.
- **EmpresaViewSet:**  
  Para usuarios no superuser, en `list()` filtrar:  
  `queryset = Empresa.objects.filter(id__in=get_empresa_ids_allowlist(request))`.

Con eso una empresa no puede ver ni tocar datos de otra.

---

## 2. MVP en 15 días: qué es corazón y qué es ruido

### Mantener (corazón – imprescindible para vender)

- **Auth:** Login JWT + PerfilUsuario (empresa + rol).  
- **Empresas:** CRUD básico (una empresa por cliente/tenant).  
- **Ventas:** Crear venta, listar por empresa, emitir factura a MH (crear DTE, firmar, enviar).  
- **Clientes:** Listado/alta para poder elegir receptor en la factura.  
- **Productos:** Por empresa, para armar detalles de la factura.  
- **Estado DTE:** Borrador → Enviado → AceptadoMH/RechazadoMH (y si añades ErrorEnvio, para reintentos).  
- **Un reporte fiscal mínimo:** Por ejemplo libro de ventas (CSV o PDF) por periodo para presentar a Hacienda.  
- **Frontend mínimo:** Login, selector de empresa (solo las permitidas), pantalla de facturación (lista + crear/emitir), descarga de PDF de una factura.

### Quitar o posponer (ruido para salir en 15 días)

- **Módulo Contabilidad completo:** Compras, liquidaciones, retenciones recibidas, anexos 161/162/163, conciliación de retenciones. → Posponer: deja solo lo que ya uses tú para un cliente piloto (ej. solo ventas + un libro de ventas).
- **Carga masiva DTE (procesar_json_dte, guardar_lote_aprobado, procesar_lote_dtes).** → Quitar del menú MVP; se puede reactivar después.
- **Descarga de lote (ZIP de PDFs/JSONs).** → Posponer.
- **Invalidación de DTE desde la app.** → Posponer (o dejar solo para superuser).
- **Libros de IVA automáticos / reportes avanzados (todos los CSV/PDF salvo uno de ventas).** → Dejar un solo reporte “Libro de ventas periodo X” en CSV o PDF.
- **Frontend:** Libro liquidaciones, gestión retenciones, carga masiva, formulario de compras. → Ocultar en el menú o no desplegar esas rutas en el MVP.

Resumen: **corazón = Login + Empresa + Clientes + Productos + Ventas + Emitir a MH + 1 reporte ventas + PDF factura.** Todo lo demás se puede etiquetar como “en desarrollo” y no mostrarlo hasta después del día 15.

---

## 3. Fallos del API de Hacienda (sin Celery/Redis)

Objetivo: que cuando falle internet o MH, la factura no se pierda y se pueda reintentar.

### Opción simple (solo lógica en backend + botón “Reintentar”)

1. **Modelo `Venta`:**  
   - Añadir a `ESTADO_DTE_CHOICES`: `('ErrorEnvio', 'Error de envío (reintentar)')`.  
   - Opcional: campo `error_envio_mensaje = models.CharField(max_length=500, blank=True, null=True)`.

2. **En la vista que llama a `FacturacionService(empresa).procesar_factura(venta)` (ej. `emitir_factura`):**  
   En el `except EnvioMHError as e` (y si quieres también `requests.RequestException`):
   - Guardar estado y mensaje:  
     `venta.estado_dte = 'ErrorEnvio'`  
     `venta.error_envio_mensaje = str(e)[:500]`  
     `venta.save()`
   - Devolver **200** con cuerpo tipo:  
     `{"exito": false, "mensaje": str(e), "reintentar": true, "venta_id": venta.id}`  
   Así el frontend no trata como “error fatal” y puede mostrar “No se pudo enviar. Reintentar”.

3. **Frontend:**  
   En la pantalla de facturación, si `estado_dte === 'ErrorEnvio'`, mostrar botón “Reintentar envío” que llame de nuevo al mismo endpoint `POST .../emitir-factura/`. El backend ya puede volver a intentar; no hace falta cola.

4. **Opcional – Reintentos automáticos sin Celery:**  
   Management command `python manage.py reintentar_envios_mh` que:
   - Haga `Venta.objects.filter(estado_dte='ErrorEnvio')` (y opcionalmente `error_envio_mensaje__isnull=False`).
   - Por cada una, llame a `FacturacionService(venta.empresa).procesar_factura(venta)`.
   - Si éxito → `estado_dte = 'AceptadoMH'`, limpiar `error_envio_mensaje`.
   - Si falla otra vez → dejar en `ErrorEnvio` y actualizar `error_envio_mensaje`.
   Programar con cron cada 10–15 minutos si quieres reintentos en background sin Redis/Celery.

Con esto cubres “Hacienda caída” o “sin internet” sin introducir colas ni brokers.

---

## 4. Infraestructura ~20 USD/mes (primeros 10 clientes)

- **Opción A – Un solo VPS:**  
  **DigitalOcean Droplet 2 GB RAM (~12 USD/mes)** o **Hetzner CX22 (~5–6 EUR)**.  
  En el mismo servidor: Django (gunicorn), Nginx (reverse proxy + estáticos), PostgreSQL en el mismo host (no managed). Backups: `pg_dump` vía cron a un bucket (DO Spaces ~5 USD o Backblaze B2 muy barato).  
  Con 10 clientes y uso moderado aguanta; no es óptimo para alta disponibilidad pero es seguro si mantienes backups y actualizaciones.

- **Opción B – Plataforma gestionada barata:**  
  **Railway** o **Render:**  
  - Railway: plan de pago por uso o ~5–20 USD/mes con PostgreSQL incluido.  
  - Render: free tier para web + PostgreSQL de pago (≈7 USD).  
  Subes el repo, configuras variables de entorno (SECRET_KEY, DB, URL del firmador), y evitas administrar servidor. Límite: en free tier el servicio puede “dormir”; para 10 clientes suele bastar un plan mínimo de pago.

- **Recomendación “20 USD”:**  
  **DigitalOcean Droplet 2 GB (12 USD) + PostgreSQL en el mismo droplet + Nginx + backups a Spaces (5 USD)**. Por debajo de 20 USD y control total. Alternativa: **Hetzner** si prefieres menos costo y aceptas datacenter en Europa (latencia un poco mayor desde El Salvador pero usable para facturación).

---

## 5. Veredicto “Vender o Morir”

### ¿Es irresponsable vender el sistema tal cual está hoy?

**Sí.** Motivos directos:

1. Cualquier usuario (o alguien que obtenga un token) puede pedir `empresa_id=2` y ver ventas/compras/reportes de otra empresa. No hay filtro por tenant.
2. La app no obliga a login: se puede entrar a “seleccionar empresa” y llamar a la API sin autenticación en varios endpoints.
3. Si MH o la red fallan, el usuario solo ve “error”; no hay estado “pendiente de envío” ni forma clara de reintentar sin que parezca que la factura se perdió.

Eso implica riesgo legal (datos de un cliente accesibles por otro) y operativo (pérdida de confianza cuando falla Hacienda).

### Las 3 cosas técnicas que SÍ o SÍ hay que cambiar para cobrar con responsabilidad mínima

1. **Filtro multi-tenant obligatorio**  
   Usar `api/utils/tenant.py` en todas las vistas que toquen datos por empresa (listas, detalle por PK, reportes, creación). Sin esto no se puede cobrar: es la única forma de que una empresa no vea datos de otra.

2. **Exigir autenticación en toda la API y login en el frontend**  
   - Backend: `REST_FRAMEWORK['DEFAULT_PERMISSION_CLASSES'] = ['rest_framework.permissions.IsAuthenticated']` y excluir solo `auth/login/`.  
   - Frontend: pantalla de login primero; guardar token y enviarlo en todas las peticiones; si no hay token, redirigir a login. Lista de empresas solo la que devuelve el login (o las permitidas para el usuario), no una llamada anónima a `/api/empresas/`.

3. **Manejo explícito de fallos de envío a MH**  
   Estado `ErrorEnvio` (o equivalente) cuando falle el envío (red/MH), guardar mensaje de error, y devolver `reintentar: true` para que el usuario pueda reintentar desde la misma pantalla (o con un comando periódico). Sin esto, cualquier caída de MH se vive como “tu sistema no sirve”.

Con esas tres cosas el sistema pasa de “irresponsable vender” a “mínimamente responsable para cobrar”: aislamiento entre clientes, acceso solo con cuenta y manejo claro de fallos de Hacienda.

---

*Documento de auditoría crítica – modo supervivencia SaaS. Implementación concreta en `api/utils/tenant.py` y en este archivo.*
