# Plan de Integración Directa con el MH — AZ DIGITAL

**Programador:** Oscar Amaya Romero  
**Objetivo:** Transmitir facturas electrónicas al Ministerio de Hacienda de El Salvador sin errores.

---

## Resumen Ejecutivo

Este documento detalla los pasos técnicos y administrativos necesarios para que AZ DIGITAL transmita Documentos Tributarios Electrónicos (DTE) directamente al Ministerio de Hacienda (MH) de El Salvador. La integración requiere trabajo en **dos frentes**: habilitación administrativa ante la DGII y desarrollo técnico.

---

## Fase 0: Habilitación Administrativa (Antes del código)

### 0.1 Solicitar incorporación como emisor electrónico

1. **Contactar a la DGII** (Dirección General de Impuestos Internos)
   - Portal: https://www.mh.gob.sv/facturación-electronica/
   - Solicitar ingreso al sistema de facturación electrónica

2. **Ambiente de pruebas**
   - Se dispone de **60 días** para demostrar capacidad técnica
   - Obtener credenciales: NIT, Clave API, usuario y contraseña
   - URL ambiente pruebas: típicamente `fesvtest.mh.gob.sv` o similar (verificar en documentación actual)

3. **Certificado de Firma Electrónica**
   - **Gratuito** — se obtiene de la DGII
   - Formato: **JWT (JSON Web Token)**
   - Se solicita para el NIT del contribuyente
   - Necesario para firmar cada DTE antes de transmitir

### 0.2 Documentación oficial a revisar

| Recurso | URL / Ubicación |
|---------|-----------------|
| Portal Facturación MH | https://factura.gob.sv/ |
| Esquemas JSON | factura.gob.sv (sección descargas) |
| Manual Funcional Sistema de Transmisión | Solicitar a DGII |
| Guía de Incorporación | Solicitar a DGII |
| Consulta DTE | https://portaldgii.mh.gob.sv/ssc/consulta/fe |

---

## Fase 1: Preparación de la Base de Datos

### 1.1 Verificar columnas en `ventas`

Ejecutar migración si no se ha hecho:

```bash
python scripts/alter_ventas_auditoria_dte.py
```

Columnas requeridas:
- `estado_dte` — Valores: `RESPALDO` | `CONTINGENCIA` | `PENDIENTE_TRANSMISION` | `TRANSMITIDO` | `RECHAZADO`
- `codigo_generacion` — UUID único por DTE (32 caracteres sin guiones)
- `numero_control` — Formato: `DTE-{tipo}-{codigo_establecimiento}-{correlativo}`
- `sello_recepcion` — Respuesta del MH (agregar si no existe)

### 1.2 Nuevo script: agregar `sello_recepcion` a ventas

```sql
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS sello_recepcion TEXT;
```

### 1.3 Tabla de cola de transmisión (opcional pero recomendado)

Para contingencia y reintentos:

```sql
CREATE TABLE IF NOT EXISTS dte_transmision_cola (
    id SERIAL PRIMARY KEY,
    venta_id INTEGER REFERENCES ventas(id),
    empresa_id INTEGER NOT NULL,
    codigo_generacion VARCHAR(64) UNIQUE NOT NULL,
    json_payload TEXT,
    intentos INTEGER DEFAULT 0,
    ultimo_intento TIMESTAMP,
    estado VARCHAR(32) DEFAULT 'PENDIENTE',
    sello_recepcion TEXT,
    error_respuesta TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Fase 2: Generación del JSON según Esquema MH

### 2.1 Tipos de DTE a implementar

| Código | Tipo DTE | Tu sistema |
|--------|----------|------------|
| 01 | Factura Consumidor Final | FACTURA |
| 03 | Comprobante de Crédito Fiscal | CREDITO_FISCAL |
| (Ticket) | Respaldos sin transmisión | TICKET — no se transmite al MH |

**Nota:** Los Tickets no se transmiten al MH; son solo respaldo interno. Solo Factura y Crédito Fiscal requieren transmisión.

### 2.2 Estructura base del JSON (referencia)

El esquema exacto debe consultarse en factura.gob.sv. Estructura típica:

```json
{
  "identificacion": {
    "codigoGeneracion": "UUID-32-CHARS-SIN-GUIONES",
    "tipoDte": "01",
    "numeroControl": "DTE-01-M000P001-000000000001",
    "tipoModelo": 1,
    "tipoOperacion": 1,
    "tipoContingencia": null,
    "motivoContin": null,
    "fechaEmision": "2024-03-22T10:30:00-06:00",
    "tipoMoneda": "USD"
  },
  "documentoRelacionado": null,
  "emisor": {
    "nit": "0614-123456-789-1",
    "nrc": "123456",
    "nombre": "Empresa Ejemplo S.A. de C.V.",
    "codigoActividad": "01111",
    "descripcionActividad": "Agricultura",
    "direccion": { "departamento": "06", "municipio": "01", ... },
    "telefono": "2222-3333",
    "correo": "info@empresa.com"
  },
  "receptor": {
    "tipoDocumento": "13",
    "numeroDocumento": "06141234567891",
    "nrc": null,
    "nombre": "Consumidor Final",
    "codigoActividad": null,
    "direccion": { ... },
    "telefono": null,
    "correo": null
  },
  "cuerpoDocumento": [
    {
      "numeroLinea": 1,
      "tipoItem": 2,
      "numeroDocumento": "PROD001",
      "cantidad": 2,
      "codigo": "PROD001",
      "descripcion": "Producto ejemplo",
      "precioUnidad": 10.00,
      "montoDescu": 0.00,
      "montoPagar": 22.60,
      "ventasNoSujetas": 0.00,
      "ventaExenta": 0.00,
      "ventaGravada": 20.00
    }
  ],
  "resumen": {
    "totalNoSujetas": 0.00,
    "totalExenta": 0.00,
    "totalGravada": 20.00,
    "subTotalVentas": 20.00,
    "descu": 0.00,
    "porcentajeDescuento": 0.00,
    "totalDescu": 0.00,
    "totalPagar": 22.60,
    "totalLetras": "VEINTIDOS DOLARES 60/100",
    "saldoFavor": 0.00,
    "condicionOperacion": 1,
    "pagos": [ { "codigoPago": "01", "montoPago": 22.60, ... } ],
    "numPagoElectronico": null
  }
}
```

### 2.3 Crear servicio `dte_venta_service.py`

Responsabilidades:
1. Generar `codigoGeneracion` (UUID v4, 32 chars sin guiones)
2. Generar `numeroControl` según formato MH
3. Mapear venta → JSON según esquema oficial
4. Validar campos obligatorios antes de transmitir

---

## Fase 3: Autenticación y Firma Digital

### 3.1 Autenticación al API MH

- **Token de acceso:** Validez 24 horas
- **Método:** POST con NIT y Clave API
- **Almacenar:** Token en cache (archivo o Redis) y renovar automáticamente

### 3.2 Firma Digital del DTE

- **Formato:** JWT
- **Certificado:** Asignado por DGII al NIT
- **Proceso:**
  1. Serializar JSON del DTE
  2. Firmar con certificado (clave privada)
  3. Adjuntar firma al payload antes de transmitir

**Librerías Python sugeridas:**
- `PyJWT` — para generar/verificar JWT
- `cryptography` — para manejo de certificados .p12/.pfx

### 3.3 Variables de entorno (.env)

```env
# MH Facturación Electrónica
MH_AMBIENTE=pruebas
MH_API_URL=https://fesvtest.mh.gob.sv/api
MH_NIT=06141234567891
MH_CLAVE_API=********
MH_CERTIFICADO_PATH=/ruta/al/certificado.p12
MH_CERTIFICADO_PASSWORD=********
```

---

## Fase 4: Transmisión al MH

### 4.1 Endpoints típicos (verificar en manual oficial)

| Acción | Método | Endpoint (ejemplo) |
|--------|--------|--------------------|
| Autenticación | POST | /auth |
| Transmitir DTE | POST | /dte/emitir |
| Consultar DTE | GET | /dte/consulta/{codigoGeneracion} |
| Evento invalidación | POST | /dte/invalidar |

### 4.2 Flujo de transmisión

```
1. Crear venta (guardar en BD)
2. Si tipo = FACTURA o CREDITO_FISCAL:
   a. Generar codigo_generacion (UUID)
   b. Generar numero_control
   c. Construir JSON según esquema MH
   d. Firmar JSON con certificado
   e. Obtener token MH (si expirado)
   f. POST al endpoint de transmisión
   g. Si 200 OK: guardar sello_recepcion, estado_dte = 'TRANSMITIDO'
   h. Si error: guardar estado_dte = 'RECHAZADO', error_respuesta; reintentar según política
3. Si falla conexión: estado_dte = 'CONTINGENCIA', encolar para retransmisión (máx 72h)
```

### 4.3 Manejo de rechazos

- Documentos rechazados: **corregir dentro de 24 horas** (normativa MH)
- Implementar cola de reintentos con backoff
- Notificar al usuario (correo o alerta en sistema)

---

## Fase 5: Contingencia

### 5.1 Cuándo usar CONTINGENCIA

- Sin conexión a internet
- API MH no responde (timeout)
- Servicio MH caído

### 5.2 Qué hacer

1. Emitir documento con `estado_dte = 'CONTINGENCIA'`
2. Guardar JSON firmado en cola
3. Proceso batch (cron o tarea programada) que reintente cada X minutos
4. **Plazo máximo:** 72 horas para transmitir

---

## Fase 6: Evento de Invalidación

Cuando se anula una venta que ya fue transmitida:

1. Verificar `estado_dte = 'TRANSMITIDO'` y que exista `sello_recepcion`
2. Construir JSON de evento de invalidación
3. Firmar y enviar al endpoint de invalidación del MH
4. Actualizar `estado_dte = 'ANULADO'` en ventas
5. Conservar motivo, usuario, fecha (ya implementado)

---

## Fase 7: Persistencia al Crear Venta

### 7.1 Cambios en `ventas_repo.crear_venta`

- Agregar parámetros: `codigo_generacion`, `numero_control`, `estado_dte`
- Insertar estos valores en el INSERT
- Para TICKET: `estado_dte = 'RESPALDO'`, codigo/numero pueden ser null
- Para FACTURA/CREDITO_FISCAL: generar UUID y numero_control antes de insertar

### 7.2 Cambios en `persistir_venta` (ventas_service)

- Si `tipo_comprobante` in ('FACTURA','CREDITO_FISCAL'):
  - Generar codigo_generacion
  - Generar numero_control (usar codigo establecimiento de sucursal)
  - Pasar a crear_venta
- Luego de commit: llamar a servicio de transmisión (síncrono o asíncrono)

### 7.3 Actualizar `sello_recepcion` tras transmisión exitosa

```sql
UPDATE ventas SET sello_recepcion = %s, estado_dte = 'TRANSMITIDO' WHERE id = %s
```

---

## Fase 8: Interfaz y Reportes

### 8.1 Comprobante impreso

- Reemplazar texto "Documento de respaldo — sin transmisión electrónica al MH" por:
  - Si `estado_dte = 'TRANSMITIDO'`: mostrar `sello_recepcion` (o indicar "Transmitido al MH")
  - Si `estado_dte = 'CONTINGENCIA'`: "Emitido en contingencia - Pendiente de transmisión"
  - Si `estado_dte = 'RECHAZADO'`: "Rechazado por MH - Ver mensaje de error"

### 8.2 QR en comprobantes

- Generar QR con URL: `https://portaldgii.mh.gob.sv/ssc/consulta/fe?codigoGeneracion={codigo_generacion}`
- Librería: `qrcode` (pip install qrcode)

### 8.3 Reporte de estado DTE

- Listar ventas con filtro por estado_dte
- Permitir retransmitir manualmente los RECHAZADOS o pendientes

---

## Orden de Implementación Sugerido

| # | Tarea | Prioridad |
|---|-------|-----------|
| 1 | Habilitación administrativa (contactar DGII) | 🔴 Crítica |
| 2 | Obtener documentación oficial (esquemas, manual) | 🔴 Crítica |
| 3 | Agregar sello_recepcion a ventas, persistir codigo_generacion/numero_control | 🔴 Alta |
| 4 | Crear dte_venta_service.py (generar JSON) | 🔴 Alta |
| 5 | Integrar firma JWT con certificado | 🔴 Alta |
| 6 | Implementar autenticación API MH | 🔴 Alta |
| 7 | Implementar transmisión POST DTE | 🔴 Alta |
| 8 | Cola de contingencia y reintentos | 🟡 Media |
| 9 | Evento de invalidación | 🟡 Media |
| 10 | QR en comprobantes | 🟢 Baja |
| 11 | Exportar JSON para crédito fiscal (envío a cliente) | 🟢 Baja |

---

## Recursos y Referencias

- **Portal MH Facturación:** https://factura.gob.sv/
- **Consulta DTE:** https://portaldgii.mh.gob.sv/ssc/consulta/fe
- **AUDITORIA_DTE.md:** Documento existente en el proyecto con contexto de anulaciones y compras

---

## Advertencia Final

Los esquemas JSON y endpoints del MH pueden cambiar. **Siempre consultar la documentación oficial más reciente** antes de implementar cada fase. Se recomienda mantener contacto con la DGII durante el proceso de integración.
