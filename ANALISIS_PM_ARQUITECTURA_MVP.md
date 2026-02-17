# Análisis Senior: PM + Arquitecto Fullstack
## Plataforma SaaS B2B – Facturación Electrónica (DTE) El Salvador

**Fecha:** 16 de febrero de 2026  
**Alcance:** Auditoría de estado actual, timeline MVP, mejoras no contempladas, hosting, viabilidad web/app y veredicto objetivo.

---

## 1. Auditoría del Estado Actual

### 1.1 Arquitectura general

| Capa | Tecnología | Estado |
|------|------------|--------|
| Backend | Django 5.x + DRF + SimpleJWT | ✅ Sólido para API y negocio |
| Base de datos | SQLite (dev) / PostgreSQL (configurado en deps) | ⚠️ Producción debe usar PostgreSQL |
| Frontend | React 19 + Vite | ✅ Estructura clara, módulos definidos |
| Integración MH | `FacturacionService` + `DTEGenerator` + firmador (Docker/remoto) | ✅ Flujo completo: token → DTE → firma → envío |

La separación Backend (Python/Django) y Frontend (React) es adecuada para un SaaS y para futura app (API primero).

### 1.2 Multi-empresa y multi-usuario: escalabilidad y seguridad

**Lo que está bien:**

- **Modelo de datos:** `Empresa` como eje; `Venta`, `Compra`, `Producto`, `Liquidacion`, `RetencionRecibida`, `Correlativo` con `ForeignKey` a `Empresa`. Escalable para muchas empresas en una sola BD.
- **PerfilUsuario:** `OneToOne` con `User`, `ForeignKey` a `Empresa` (nullable para MASTER), roles MASTER / ADMINISTRADOR / VENDEDOR. Permite multi-usuario por empresa y super-admin.
- **Correlativos DTE:** Por empresa, tipo DTE y año. Correcto para numeración legal.

**Problemas críticos de seguridad (cuello de botella):**

1. **Sin aislamiento por tenant en la API:**  
   Casi todos los endpoints reciben `empresa_id` por query o body y filtran por él, pero **nunca validan** que el usuario autenticado tenga derecho a esa empresa. Cualquier usuario que conozca un `empresa_id` ajeno podría:
   - Listar ventas/compras/productos de otra empresa.
   - Descargar reportes fiscales de otra empresa.
   - Emitir facturas asociadas a otra empresa (si el flujo lo permite).

2. **Frontend no exige login:**  
   `SeleccionEmpresa` carga `/api/empresas/` sin token. Si el backend no exige autenticación en ese endpoint, la lista de empresas es pública. No hay pantalla de login obligatoria antes de elegir empresa.

3. **Credenciales sensibles en texto plano:**  
   En `Empresa`: `clave_api_mh`, `clave_certificado` (y comentarios que indican “considerar encriptación”). Para un SaaS comercial esto es riesgo regulatorio y de reputación.

4. **REST Framework sin permisos por defecto:**  
   No hay `DEFAULT_PERMISSION_CLASSES` (ej. `IsAuthenticated`) ni permisos por vista/ViewSet. La API es “abierta” por defecto.

**Conclusión auditoría 1:**  
La **estructura** de BD para multi-empresa y multi-usuario es **escalable**. La **seguridad** actual **no es adecuada para comercializar**: hace falta obligar autenticación, validar empresa permitida por usuario en cada request y endurecer almacenamiento de secretos (env/encryption).

---

## 2. Estimación realista (timeline MVP comercial)

**Progreso actual (resumido):**

- Backend: modelos, API CRUD, integración MH (generar DTE, firmar, enviar), reportes CSV/PDF (libros compras/ventas, liquidaciones, retenciones), historial de ventas, correlativos.
- Frontend: selector de empresa, portal de módulos (Facturación / Contabilidad), pantallas de facturación (panel, nueva factura), contabilidad (compras, libros IVA, liquidaciones, retenciones, carga masiva).
- Falta: autenticación obligatoria en flujo UX, autorización por empresa en API, contingencia MH, reportería automática, dashboard de ventas, soporte, hardening de seguridad y certificación/firmas en producción.

**Estimación por fases (una persona fullstack, asumiendo dedicación casi exclusiva):**

| Fase | Trabajo | Semanas |
|------|--------|--------|
| **A. Seguridad y multi-tenant** | Login obligatorio en frontend; JWT en todas las llamadas; middleware o mixin que restrinja `empresa_id` al perfil del usuario; cifrado/env de secretos Empresa | 2–3 |
| **B. Pruebas y robustez MH** | Tests automatizados (auth MH, firma, envío mock); manejo explícito de errores MH (rechazos, timeouts, 5xx); reintentos con backoff; mensajes claros al usuario | 2 |
| **C. Certificación y firma en producción** | Certificado real (no solo pruebas); validación de vencimiento; documentación para el cliente (guía de certificados) | 1–2 |
| **D. Contingencia MH** | Cola de envíos (Celery + Redis o equivalente); modo “pendiente de envío” cuando MH no responde; reintentos programados; opcional: DTE con tipoContingencia si MH lo exige | 2–3 |
| **E. Reportería fiscal “automática”** | Libros de IVA generables por periodo (ya existen reportes); programar generación mensual y descarga/email (Cron + tarea asíncrona) | 1 |
| **F. Ajustes MVP** | Dashboard básico de métricas (ventas del mes, facturas emitidas, estado MH); página de estado del sistema / MH; documentación mínima de uso | 1–2 |
| **G. Despliegue y pruebas de estrés** | Migrar a PostgreSQL; env de producción; despliegue en cloud; pruebas de carga (envíos masivos, muchos usuarios) | 2 |

**Total orientativo:** **12–16 semanas** (3–4 meses) para un **MVP comercial** con seguridad correcta, manejo de errores y contingencia MH, certificación real y despliegue estable.

**Fecha de lanzamiento sugerida:** Si se empieza ya y no hay bloqueos (certificados, contratos MH, etc.), un **MVP comercial razonable** podría estar listo en **junio–julio 2026**. Incluir 2–4 semanas de colchón para imprevistos (cambios de MH, auditorías, feedback beta).

---

## 3. Propuestas de mejora (lo no contemplado)

### 3.1 Reportería fiscal automática (Libros de IVA)

- **Estado actual:** Hay endpoints para CSV/PDF de compras, ventas CCF, ventas CF por `empresa_id` y periodo. Es “bajo demanda”.
- **Para SaaS:**  
  - Programar generación mensual (p. ej. día 1 o 5 del mes) por empresa.  
  - Guardar archivos en almacenamiento (S3/compatible) y/o enviar por email.  
  - Opcional: vista “Libros generados” con descarga y estado (generado / pendiente / error).  
- **Esfuerzo:** Bajo-medio (1–2 sem) con Celery + Cron y un modelo “ReporteFiscal” o similar.

### 3.2 Dashboard de métricas de ventas

- **Estado actual:** Panel de facturación muestra listado; no hay KPIs ni gráficos.
- **Para el dueño del negocio:**  
  - Ventas del mes / trimestre (por empresa).  
  - Número de facturas emitidas (CF vs CCF).  
  - Monto de IVA (devengado/retenido) por periodo.  
  - Gráfico simple (barras/líneas) de evolución.  
- **Backend:** Endpoints de agregación (por empresa, periodo) ya encajan en el modelo actual.  
- **Esfuerzo:** 1–2 sem (endpoints + frontend con gráficos, ej. Chart.js o similar).

### 3.3 Sistema de tickets de soporte integrado

- **Estado actual:** No existe.
- **Para SaaS B2B:**  
  - Módulo “Soporte” o “Ayuda”: el usuario abre un ticket (asunto, descripción, empresa).  
  - Backend: modelo `Ticket` (empresa, usuario, estado, mensajes).  
  - Listado “Mis tickets” y detalle con conversación.  
  - Opcional: notificaciones por email y panel interno para tu equipo.  
- **Alternativa rápida:** Integrar con herramienta externa (Zendesk, Freshdesk, Intercom) y solo un botón “Abrir ticket” que lleve a su formulario con contexto (empresa, usuario).  
- **Esfuerzo:** 2–3 sem (integrado) vs 2–3 días (integración externa).

### 3.4 Manejo de contingencia (caída del servidor MH)

- **Estado actual:** Llamadas HTTP directas con `timeout=60`; si MH no responde o devuelve 5xx, la operación falla y la venta puede quedar en estado inconsistente. No hay cola ni reintentos.
- **Recomendación:**  
  1. **Cola de envíos:** Al “emitir factura”, si MH falla por timeout/5xx, guardar la intención en una tabla “EnvioDTEPendiente” (venta_id, payload, intentos) y responder al usuario “Factura en cola; se enviará cuando MH esté disponible”.  
  2. **Worker (Celery):** Tarea periódica que reintente envíos pendientes con backoff (ej. 5 min, 15 min, 1 h).  
  3. **Estado en venta:** Ej. `estado_dte = 'PendienteEnvio'` además de Borrador/Enviado/AceptadoMH/RechazadoMH.  
  4. **Opcional (según normativa MH):** Uso de `tipoContingencia` en el DTE cuando MH permita contingencia oficial.  
- **Esfuerzo:** 2–3 sem (cola + worker + estados + UI de “pendientes”).

---

## 4. Estrategia de hosting y despliegue (para venta)

Objetivos: buena latencia desde **El Salvador**, escalar con el número de empresas y costos alineados a suscripción.

### 4.1 Latencia desde El Salvador

- **AWS (us-east-1, N. Virginia):** ~80–120 ms desde SV. Aceptable para APIs REST.
- **Google Cloud (us-east1 / southamerica-east1):** Similar o algo mejor si usas región cercana; southamerica suele ser más caro.
- **DigitalOcean:** Datacenters en NYC/AMS; latencia desde SV ~100–150 ms. Aceptable para SaaS administrativo.
- **Conclusión:** Cualquiera de los tres es viable. La diferencia no suele ser crítica para facturación/contabilidad; importa más tener CDN para estáticos y API bien cacheable donde aplique.

### 4.2 Costos vs rendimiento (modelo suscripción)

Escenario: decenas de empresas, uso moderado (no millones de requests/día).

| Opción | Ejemplo | Costo/mes aprox. | Comentario |
|--------|--------|-------------------|------------|
| **DigitalOcean App Platform** | 1 app backend + 1 worker (Celery) + PostgreSQL managed | 30–60 USD | Muy buen equilibrio; despliegue simple; escalado vertical fácil. |
| **AWS** | EC2 pequeño (t3.small) + RDS (PostgreSQL) + ElastiCache (Redis) para cola | 80–150 USD | Más control y opciones; mayor complejidad operativa. |
| **Google Cloud Run + Cloud SQL** | Backend en containers sin servidor + PostgreSQL | 50–120 USD | Escala a cero útil si el tráfico es muy variable. |

**Recomendación:**  
- Para **lanzar rápido y mantener costos bajos:** **DigitalOcean** (App Platform o Droplet + Managed DB + Redis).  
- Si ya tienes experiencia en **AWS** y planeas más productos o integraciones enterprise: **AWS** (EC2 + RDS + S3 para PDFs/certificados).  
- **Backups:** Automatizar backups diarios de BD y de archivos críticos (certificados, logos); retención mínima 7–30 días.

### 4.3 Escalabilidad

- **Corto plazo:** Una instancia de aplicación + PostgreSQL + Redis es suficiente para decenas de empresas y cientos de usuarios.  
- **Mediano plazo:** Añadir worker(s) para Celery (envíos MH, reportes, emails); separar estáticos (S3/Spaces + CDN).  
- **Largo plazo:** Revisar límites de MH (rate limits); si hace falta, cola por empresa y prioridad; caché de consultas pesadas (resúmenes, dashboards).

---

## 5. Viabilidad Web + App

### 5.1 ¿Mantener una sola base de código para web y app móvil?

- **Sí es realista** si el producto se diseña “API first”: toda la lógica de negocio y datos está en el backend; frontend web y app solo consumen la misma API.
- Tu proyecto **ya es API first**: React consume REST; no hay lógica crítica solo en el frontend. Una app móvil podría reutilizar los mismos endpoints.

### 5.2 React vs React Native vs PWA

| Opción | Pros | Contras |
|--------|------|--------|
| **Seguir con React (web)** | Ya está hecho; un solo equipo web. | App “nativa” requeriría otro proyecto (React Native o Flutter). |
| **React Native** | Una base de código (JS/React) para iOS y Android; acceso a dispositivo (notificaciones, cámara). | Otro stack de build y despliegue; diferencias de componentes y navegación respecto a web. |
| **PWA (Progressive Web App)** | Mismo código React; “instalable” desde el navegador; notificaciones y caché offline posibles. | Limitaciones en acceso nativo (ej. algunas APIs de firma o impresión); percepción de “no es una app de verdad” en algunos usuarios. |

**Recomendación:**  
- **Corto plazo:** Mantener **React (web)** y, si quieres “app” rápido, convertir el frontend en **PWA** (service worker, manifest, HTTPS). Así el cliente puede “añadir a la pantalla de inicio” y usar la misma app en escritorio y móvil.  
- **Mediano plazo:** Si el negocio exige app en tiendas (iOS/Android), valorar **React Native** compartiendo lógica (hooks, servicios API) con la web donde sea posible, o un monorepo con paquetes compartidos.  
- No es necesario “pasar” toda la arquitectura a React Native de entrada; el backend y la API siguen siendo el núcleo.

---

## 6. Veredicto objetivo

### 6.1 ¿Es lograble terminar esto para comercializar con los recursos y tecnologías actuales?

**Sí**, siempre que se priorice:

1. **Seguridad multi-tenant** (autenticación obligatoria + restricción de `empresa_id` por usuario).  
2. **Contingencia y robustez frente a MH** (cola, reintentos, estados claros).  
3. **Certificación y firma en producción** (certificados reales, no solo ambiente de pruebas).  
4. **Despliegue estable** (PostgreSQL, variables de entorno, backups).

Las tecnologías (Django, DRF, React, integración MH) son adecuadas y el avance actual es suficiente para construir un MVP comercial en **3–4 meses** con foco en lo anterior.

### 6.2 Cuellos de botella más peligrosos

1. **Seguridad:**  
   Si se comercializa sin corregir el control de acceso por empresa, un solo incidente (acceso a datos de otra empresa o fuga de reportes) puede hundir la confianza y generar responsabilidad legal. **Prioridad máxima.**

2. **Dependencia de MH:**  
   Sin cola ni contingencia, un día de caída o lentitud de MH se traduce en “no puedo facturar” y soporte saturado. Los clientes B2B lo viven muy mal. **Prioridad alta.**

3. **Certificados digitales:**  
   Vencimiento, renovación y configuración por empresa son complejos para el usuario. Si no se documenta y se acompaña (onboarding o soporte), habrá rechazos y frustración. **Prioridad alta.**

4. **Recursos humanos:**  
   Una sola persona fullstack puede llevar el MVP, pero cualquier baja o cambio de prioridades alarga mucho la fecha. Un segundo recurso (o outsourcing acotado para frontend o DevOps) reduce riesgo.

5. **Normativa y cambios de MH:**  
   Cambios en esquemas, ambientes o requisitos de contingencia pueden exigir ajustes de código y pruebas. Mantener un canal (newsletter, portal MH) y reservar tiempo para adaptaciones.

### 6.3 Resumen en una frase

**El producto es viable y la base técnica es buena; el MVP comercial es alcanzable en 3–4 meses si se cierran primero la seguridad multi-tenant y la contingencia MH, y se asume que sin eso no se debe vender a terceros.**

---

*Documento generado a partir del análisis del código y la arquitectura del repositorio (backend Django, frontend React, integración MH, modelos y vistas revisados).*
