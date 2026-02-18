# Informe CTO: Análisis Crítico del Sistema de Facturación Electrónica

**Fecha:** 18 de febrero de 2026  
**Rol:** CTO / Arquitecto de Software  
**Alcance:** Auditoría técnica profunda para decisión de lanzamiento Beta

---

## ACTUALIZACIÓN: Correcciones Aplicadas (18 feb 2026)

Se han implementado las siguientes correcciones P0 y P1:

| Item | Estado |
|------|--------|
| Contraseña hardcodeada eliminada | ✅ Usa `self.empresa.clave_api_mh` |
| Mapeo AMBIENTE corregido | ✅ 00=Producción, 01=Pruebas (alineado con modelo) |
| `select_for_update()` en correlativos | ✅ + retry por IntegrityError |
| `print()` → logging | ✅ Eliminados todos los prints de debug |
| SECRET_KEY, DEBUG, ALLOWED_HOSTS | ✅ Desde variables de entorno |
| Validación tenant en endpoints | ✅ Dashboard, ventas, compras, reportes, libros IVA, etc. |
| Estado PendienteEnvio | ✅ Nuevo estado + EnvioMHTransitorioError para timeout/5xx |
| Crear venta/compra con validación | ✅ require_empresa_allowed en body |

**Pendiente para siguiente iteración:** Cola de reintentos (Celery+Redis), cifrado de credenciales.

---

## Resumen Ejecutivo

**El sistema NO está listo para usuarios Beta en producción.** La base arquitectónica es sólida (Django, DRF, integración MH, modelo de datos), pero existen **vulnerabilidades de seguridad críticas**, **bugs que romperían facturación en producción** y **ausencia de contingencia ante fallos de MH**. Un lanzamiento ahora implicaría riesgo alto de pérdida de datos, fuga de información fiscal y colapso ante carga moderada.

---

## 1. Panorama Actual: ¿Arquitectura sólida o conjunto de parches?

### Veredicto: **Híbrido — base correcta con puntos de quiebre**

| Aspecto | Estado | Comentario |
|---------|--------|------------|
| Stack tecnológico | ✅ Adecuado | Django 5/6, DRF, React, PostgreSQL (Docker) |
| Modelo de datos | ✅ Bien diseñado | Empresa, Venta, DetalleVenta, Correlativo, Cliente |
| Integración MH | ⚠️ Funcional con bugs | Flujo completo: DTE → firma → envío, pero con errores críticos |
| Multi-tenancy | ❌ Parcial | Existe `tenant.py` pero NO se aplica consistentemente |
| Separación de capas | ✅ Clara | Backend API, frontend React, servicios desacoplados |

**Problema estructural:** La validación por tenant (`require_empresa_allowed`) existe pero **solo se aplica en ~8 de 50+ endpoints**. El resto confía en `empresa_id` del request sin validar que el usuario tenga permiso. Es un patrón inconsistente que genera agujeros de seguridad.

---

## 2. Factibilidad de Beta: ¿Es viable lanzar ahora?

### Respuesta: **No. Alto riesgo de incidentes graves.**

### 2.1 Riesgo de pérdida de datos

| Escenario | Probabilidad | Impacto | Mitigación actual |
|-----------|--------------|---------|-------------------|
| Fallo MH durante envío (timeout, 5xx) | Alta | Venta queda en Borrador/RechazadoMH con mensaje genérico; usuario no sabe si reenviar | ❌ Ninguna. No hay cola ni reintentos. |
| Proceso interrumpido tras crear venta, antes de respuesta MH | Media | Venta en BD con correlativo asignado pero sin confirmación; posible duplicado si reintenta | ⚠️ Parcial. El servicio actualiza estado en `except`, pero no hay idempotencia. |
| Correlativos duplicados bajo concurrencia | Media | Dos facturas con mismo número de control → rechazo MH y problemas fiscales | ❌ `obtener_siguiente_correlativo` no usa `select_for_update()` |
| Caída de MH prolongada | Alta | "No puedo facturar" durante horas. Sin modo contingencia. | ❌ No hay cola, ni estado "PendienteEnvio" |

### 2.2 Riesgo en comunicación con la API tributaria (MH)

- **Timeout fijo 60s:** Si MH responde lento, el usuario espera 1 minuto y recibe error. No hay retry automático.
- **Sin circuit breaker:** Si MH devuelve 5xx en cascada, cada request sigue intentando → saturación.
- **Credenciales:** Contraseña API MH hardcodeada en código (ver sección 4) → **todas las empresas usan la misma contraseña o fallan**.

### 2.3 Conclusión Beta

**No se recomienda abrir a usuarios reales** hasta resolver como mínimo:

1. Bug de contraseña hardcodeada  
2. Validación tenant en todos los endpoints sensibles  
3. Contingencia básica (cola de envíos pendientes + reintentos)  
4. Correlativos con `select_for_update` para concurrencia  

---

## 3. Puntos de Quiebre (Critical Failures)

### 3.1 Con 100 usuarios simultáneos

| Componente | Comportamiento esperado | Riesgo |
|------------|-------------------------|--------|
| **Correlativos** | Posible duplicado de `numero_control` entre dos ventas de la misma empresa | **Alto.** Sin `select_for_update()`, dos requests pueden leer el mismo `ultimo_correlativo`, incrementar y guardar → mismo número. MH rechazará la segunda. |
| **SQLite en desarrollo** | Lock de escritura; un solo writer a la vez | **Alto.** Si se desplegara por error con SQLite, colapso rápido. |
| **Gunicorn single worker** | Un proceso; requests en cola | **Medio.** Latencia alta; timeouts de frontend (30s) pueden dispararse antes de que el backend responda. |
| **MH** | Rate limits no documentados en el código | **Desconocido.** Posible throttling o bloqueo si hay muchos envíos en paralelo. |

### 3.2 Fallo a mitad de transacción

**Flujo actual de `crear_venta_con_detalles`:**

1. `VentaConDetallesSerializer.create()` → transacción atómica: crea `Venta` + `DetalleVenta` + asigna `numero_control` (si estado=Generado)  
2. **Fuera de la transacción:** `FacturacionService.procesar_factura(venta)` → Auth MH, firma, envío  
3. Si MH falla: se captura excepción, se actualiza `venta.estado_dte`, se re-lanza `FacturacionServiceError`

**Problema:** Si el proceso muere (OOM, kill, crash) entre el paso 1 y el 2, o durante el 2, la venta queda con `estado_dte='Generado'` o `'Borrador'` y ya tiene `numero_control` asignado. Al reintentar, podría generarse otro correlativo (si se crea una venta nueva) → duplicado. O el usuario no sabe si debe reenviar la misma venta. **No hay idempotencia ni estado "PendienteEnvio".**

### 3.3 Inconsistencia AMBIENTE Modelo vs Servicio

En `Empresa` (models.py):

- `'00'` = PRODUCCION  
- `'01'` = PRUEBAS  
- Default: `'01'`

En `FacturacionService` (facturacion_service.py):

- `'00'` → URL **Pruebas** (apitest.dtes.mh.gob.sv)  
- `'01'` → URL **Producción** (api.dtes.mh.gob.sv)  

**Las etiquetas están invertidas.** Una empresa nueva con default `'01'` enviaría a **PRODUCCIÓN**, no a pruebas. Riesgo de enviar facturas reales al ambiente incorrecto.

---

## 4. Lo que está MAL (Debilidades)

### 4.1 Seguridad — Crítico

1. **Contraseña API MH hardcodeada** (`facturacion_service.py:130`)
   ```python
   pwd = "2Caballo.azul"  # Forzando contraseña correcta para prueba
   ```
   - Todas las empresas usan esta contraseña. Cualquier empresa con otra contraseña fallará en auth.
   - Debe usarse `self.empresa.clave_api_mh`.

2. **Credenciales en texto plano**
   - `clave_api_mh`, `clave_certificado` en modelo `Empresa` sin cifrado.
   - Comentarios admiten "considerar encriptación en producción" — no implementado.

3. **SECRET_KEY fija** (`settings.py`)
   - `SECRET_KEY = 'django-insecure-...'` hardcodeada.
   - Debe venir de variable de entorno.

4. **DEBUG=True, ALLOWED_HOSTS=['*']**
   - Inaceptable para producción.

5. **Falta validación tenant en la mayoría de endpoints**
   - `dashboard_stats_api`: devuelve ventas de **todas** las empresas.
   - `crear_venta_con_detalles` / `crear_venta`: aceptan `empresa_id` en body sin validar; un usuario puede facturar a nombre de otra empresa.
   - `crear_compra`, `listar_compras`, `borrar_compra`, `actualizar_compra`: sin `require_empresa_allowed` ni `require_object_empresa_allowed`.
   - Reportes CSV/PDF (`reporte_csv_compras_empresa`, `reporte_pdf_ventas_ccf_empresa`, etc.): reciben `empresa_id` por query y hacen `Empresa.objects.get(id=empresa_id)` sin validar permisos → **cualquier usuario autenticado puede descargar libros fiscales de otra empresa**.
   - `procesar_json_dte`, `guardar_lote_aprobado`: sin validación tenant.
   - `download_batch_ventas`: filtra por `empresa_id` pero no valida `require_empresa_allowed`.

6. **Clientes globales**
   - `Cliente` no tiene `empresa_id`. Todos comparten el mismo directorio. Puede ser intencional, pero `clientes_api` devuelve todos los clientes sin filtro por empresa → fuga de información si se esperaba aislamiento.

### 4.2 Lógica de negocio y concurrencia

7. **Correlativos sin lock**
   - `Correlativo.objects.get_or_create(...)` + `ultimo_correlativo += 1` + `save()` dentro de `transaction.atomic()` pero **sin `select_for_update()`**.
   - Con varios workers o alta concurrencia, duplicados posibles.

8. **Headers X-Company-ID ignorados**
   - El frontend envía `X-Company-ID`; el backend **nunca lo usa**. La validación viene de `PerfilUsuario.empresa`, no del header. Si un usuario tiene múltiples empresas (MASTER), no hay forma de restringir por contexto de la pestaña actual.

### 4.3 Resiliencia y operación

9. **Sin cola de envíos a MH**
   - Si MH no responde o devuelve 5xx, el usuario ve error. No hay cola, ni reintentos, ni estado "PendienteEnvio".

10. **Print y debug en producción**
    - `facturacion_service.py`: múltiples `print()` con JSON completo del DTE, credenciales implícitas en logs.
    - Debe usarse solo `logging` con niveles adecuados.

11. **SQLite por defecto**
    - `settings.py` usa SQLite. Producción debe usar PostgreSQL vía `dj-database-url` o similar. No está claro si el despliegue actual lo sobreescribe.

### 4.4 Deuda técnica

12. **views.py ~3000 líneas**
    - Monolito difícil de mantener. Debería dividirse en módulos (ventas, compras, reportes, etc.).

13. **Duplicación de lógica**
    - Varios reportes repiten el patrón `empresa_id` + `Empresa.objects.get` sin un mixin o decorador común para tenant.

---

## 5. Lo que está BIEN (Fortalezas)

### 5.1 Arquitectura y diseño

1. **Modelo de datos coherente**
   - `Venta`, `DetalleVenta`, `Empresa`, `Cliente`, `Correlativo` bien relacionados.
   - Correlativos por empresa, tipo DTE y año.

2. **Patrón Strategy en DTE**
   - Builders por tipo (DTE-01, 03, 05, etc.), director, `generar_dte()` centralizado.
   - Fácil extender nuevos tipos.

3. **Transacciones en serializers**
   - `VentaConDetallesSerializer.create()` y `VentaSerializer.create()` usan `@transaction.atomic`.
   - Creación de venta + detalles atómica.

4. **Manejo de errores en FacturacionService**
   - Excepciones tipadas (`AutenticacionMHError`, `FirmaDTEError`, `EnvioMHError`).
   - Actualización de estado de venta en bloques `except`.

### 5.2 Seguridad (parcial)

5. **JWT con Simple JWT**
   - Access 8h, refresh 1 día.
   - Login por username o email.

6. **Permisos por rol**
   - `IsAdminUser`, `IsContadorUser`, `IsVendedorUser` en permisos.py.
   - Algunos endpoints restringen por rol (emitir, invalidar).

7. **Utilidades tenant**
   - `get_empresa_ids_allowlist`, `require_empresa_allowed`, `require_object_empresa_allowed` bien implementadas.
   - El problema es el **uso inconsistente**, no el diseño.

### 5.3 Integración MH

8. **Flujo completo**
   - Auth → Generar DTE → Firmar (interna o externa) → Enviar.
   - Soporte pruebas y producción (aunque con bug de mapeo ambiente).

9. **Invalidación de DTE**
   - Método `invalidar_dte` implementado según esquema MH.

### 5.4 DevOps

10. **Docker Compose para producción**
    - PostgreSQL, backend, frontend, nginx.
    - Volúmenes para BD, estáticos y media.

11. **Firma interna**
    - `USE_INTERNAL_FIRMADOR` permite prescindir del contenedor firmador externo.

---

## 6. Plan de Mejora Inmediato (Prioridades antes del primer cliente)

### P0 — Bloqueantes (hacer sí o sí)

| # | Acción | Esfuerzo | Archivos principales |
|---|--------|----------|----------------------|
| 1 | **Eliminar contraseña hardcodeada** en `obtener_token()`; usar `self.empresa.clave_api_mh` | 5 min | `facturacion_service.py` |
| 2 | **Corregir mapeo AMBIENTE** entre modelo y URLs MH (unificar convención 00/01) | 30 min | `models.py`, `facturacion_service.py` |
| 3 | **Validación tenant en todos los endpoints** que usan `empresa_id` o datos por empresa | 2–3 días | `views.py` (múltiples funciones) |
| 4 | **Añadir `select_for_update()`** en `obtener_siguiente_correlativo` | 30 min | `dte_generator.py` |
| 5 | **Quitar `print()`** y reemplazar por `logger` con nivel adecuado | 1 h | `facturacion_service.py` |
| 6 | **SECRET_KEY, DEBUG, ALLOWED_HOSTS** desde variables de entorno | 30 min | `settings.py` |

### P1 — Alta prioridad (antes de Beta)

| # | Acción | Esfuerzo |
|---|--------|----------|
| 7 | Cola de envíos pendientes (Celery + Redis o tabla `EnvioDTEPendiente`) + worker con reintentos | 2–3 días |
| 8 | Estado `PendienteEnvio` en `Venta.estado_dte` cuando MH falla por timeout/5xx | 1 día |
| 9 | Validar `require_empresa_allowed` en `crear_venta_con_detalles` y `crear_venta` para `empresa_id` del body | 2 h |
| 10 | Filtrar `dashboard_stats_api` por `empresa_id` (header o query) y `require_empresa_allowed` | 1 h |
| 11 | Cifrado de `clave_api_mh` y `clave_certificado` (ej. `django-fernet-fields` o cifrado en aplicación) | 1–2 días |

### P2 — Mejora (post-Beta inicial)

| # | Acción |
|---|--------|
| 12 | Refactorizar `views.py` en módulos |
| 13 | Tests automatizados (auth MH mock, correlativos, tenant) |
| 14 | Documentar rate limits de MH y añadir backoff |
| 15 | Health check de MH (endpoint `/api/health/mh`) |

---

## 7. Conclusión Final

El sistema tiene una **base técnica adecuada** para un SaaS de facturación electrónica en El Salvador. La integración con MH está implementada, el modelo de datos es correcto y la separación frontend/backend es clara.

Sin embargo, **no debe abrirse a usuarios Beta en el estado actual** por:

1. Bug crítico de contraseña hardcodeada que rompe o compromete la autenticación con MH.  
2. Inversión de ambientes (Pruebas/Producción) que puede enviar facturas reales al ambiente equivocado.  
3. Ausencia de validación tenant en la mayoría de endpoints → riesgo de acceso a datos fiscales de otras empresas.  
4. Correlativos vulnerables a duplicados bajo concurrencia.  
5. Sin contingencia ante caídas o lentitud de MH.

Con el **Plan P0 completado** (estimado 1–2 días de trabajo enfocado), se podría plantear un **Beta cerrado y supervisado** con pocos usuarios. Para un Beta amplio o comercial, se recomienda además el **Plan P1**.

---

*Documento generado a partir del análisis del código en el repositorio (backend Django, frontend React, integración MH, modelos, vistas, serializers y configuración).*
