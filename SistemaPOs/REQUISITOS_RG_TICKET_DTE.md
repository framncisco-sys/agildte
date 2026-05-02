# Requisitos de Representación Gráfica (RG) — Tickets y DTE en El Salvador

**Programador:** Oscar Amaya Romero  
**Fuente:** Ley y normativa del Ministerio de Hacienda (MH) — Facturación electrónica

---

## 1. ¿Por qué se sigue imprimiendo si es electrónico?

Aunque el documento legal sea un archivo digital (JSON), la ley en El Salvador exige que el comercio entregue un **respaldo físico o digital que el cliente pueda leer fácilmente**. Razones principales:

| Razón | Descripción |
|-------|-------------|
| **Control en carretera** | Si la policía o delegados de Hacienda detienen a alguien saliendo del establecimiento, el ticket físico demuestra que la mercadería fue pagada legalmente. |
| **Derecho del consumidor** | No todos los salvadoreños tienen smartphone o correo electrónico para revisar un JSON en el momento. |
| **Respaldos de Crédito Fiscal** | Muchas empresas prefieren engrapar el ticket físico a sus cheques o comprobantes de pago internos para sus controles contables. |

---

## 2. Diferencia entre "Ticket de antes" y "DTE de ahora"

El ticket actual debe incluir datos que antes no existían. Para que el sistema cumpla con la RG obligatoria, **el ticket debe incluir**:

| Elemento | Descripción |
|----------|-------------|
| **Código de Generación** | Un código único de 36 caracteres (UUID sin guiones, 32 chars). |
| **Número de Control** | Número secuencial con formato `DTE-01-...` o `DTE-03-...` según tipo. |
| **Sello de Recepción** | El número que Hacienda devolvió al recibir el archivo (solo si fue transmitido). |
| **Código QR** | **Lo más importante.** Al escanear con el celular debe llevar a la página oficial de Hacienda donde dice "Documento Válido". |

**URL del QR:** `https://portaldgii.mh.gob.sv/ssc/consulta/fe?codigoGeneracion={codigo_generacion}`

---

## 3. Implementación en AZ DIGITAL

### 3.1 Impresora recomendada

No se necesita una impresora láser cara. La mayoría de negocios usan **impresoras térmicas de 80 mm**.

### 3.2 Template para ticket térmico

El template debe:

1. Recibir la respuesta de Hacienda (el **Sello de Recepción**).
2. Generar el **código QR** (usar la librería `qrcode` de Python).
3. Formatear el texto para que quepa en el ancho del papel térmico (80 mm ≈ 32 caracteres por línea).

### 3.3 Ticket para Crédito Fiscal (CCF)

Cuando es Crédito Fiscal, el ticket suele ser **más largo** porque debe incluir obligatoriamente:

- **Nombre del cliente** (empresa).
- **NRC y NIT/DUI** del cliente.
- **Desglose detallado del IVA** (13%).
- Si hubo **retención del 1%**, debe aparecer claramente restada del total.

---

## 4. Estado actual del proyecto

### 4.1 `ticket_print.html` (Ticket 80 mm)

| Requisito | Estado |
|-----------|--------|
| Formato 80 mm | ✅ Implementado |
| Código de Generación | ❌ No incluido |
| Número de Control | ❌ No incluido |
| Sello de Recepción | ❌ No incluido |
| Código QR | ❌ No incluido |
| Desglose IVA / Retención | ⚠️ Parcial (gravadas, IVA, total) |

**Nota:** Este template se usa solo para `tipo_comprobante = TICKET`. Si un TICKET no se transmite al MH, no requiere código de generación ni QR. Pero si el negocio emite Factura o CCF y imprime en papel térmico (modo ticket), **sí** debe incluir esos elementos.

### 4.2 `comprobante_sv_print.html` (Comprobante A4)

| Requisito | Estado |
|-----------|--------|
| Código de Generación | ✅ Se pasa al template (pero se genera nuevo UUID en cada impresión — debería venir de BD) |
| Número de Control | ✅ Se pasa al template |
| Sello de Recepción | ⚠️ Texto fijo "Documento de respaldo — sin transmisión electrónica al MH" |
| Código QR | ❌ Placeholder; no hay imagen QR real |
| Desglose IVA / Retención | ✅ Completo |

### 4.3 Base de datos

- `ventas`: tiene `estado_dte`, `codigo_generacion`, `numero_control` (por `alter_ventas_auditoria_dte.py`).
- `sello_recepcion`: **no** está en el script de migración; debe agregarse.
- `get_venta`: **no** retorna `codigo_generacion`, `numero_control`, `sello_recepcion`, `estado_dte`.

---

## 5. Opción: Ahorrar papel

Para ahorrar papel (beneficio de la factura electrónica), el sistema puede:

1. **Preguntar al cliente:** "¿Desea imprimir ticket o prefiere envío por WhatsApp/Correo?"
2. Si elige **digital**: ahorrar papel térmico, pero **siempre** generar el PDF por si acaso.

---

## 6. Plan de acción — IMPLEMENTADO ✅

| # | Tarea | Estado |
|---|-------|--------|
| 1 | Agregar columna `sello_recepcion` a `ventas` (si no existe) | ✅ `scripts/alter_ventas_auditoria_dte.py` |
| 2 | Incluir en `get_venta` los campos DTE: `codigo_generacion`, `numero_control`, `sello_recepcion`, `estado_dte` | ✅ `ventas_repo.get_venta` |
| 3 | Agregar librería `qrcode` a `requirements.txt` | ✅ `qrcode[pil]>=7.4` |
| 4 | Generar QR real en `comprobante_sv_print.html` y mostrar `sello_recepcion` según `estado_dte` | ✅ `azdigital/utils/qr_dte.py` + template |
| 5 | Crear plantilla `ticket_dte_print.html` para Factura/CCF en papel 80 mm con RG completa | ✅ `templates/ticket_dte_print.html` |
| 6 | Usar valores de BD (no generar nuevos) al imprimir comprobante | ✅ Ruta `imprimir_ticket` |
| 7 | Opción ticket térmico vs comprobante A4 para Factura/CCF | ✅ Confirm en `ventas.html` tras guardar |

**Uso:** Para Factura o Crédito Fiscal, tras guardar la venta se pregunta "¿Imprimir en papel térmico 80mm?". Para ticket térmico: `/imprimir_ticket/<id>?formato=ticket&copias=2`

---

## Referencias

- **PLAN_INTEGRACION_MH.md** — Integración técnica con MH
- **AUDITORIA_DTE.md** — Contexto de anulaciones
- Portal MH: https://factura.gob.sv/
- Consulta DTE: https://portaldgii.mh.gob.sv/ssc/consulta/fe
