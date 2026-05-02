# Guía de Auditoría DTE — AZ DIGITAL

**Programador:** Oscar Amaya Romero

## 1. Control de Anulaciones

### Implementado
- **Soft-delete:** Las ventas anuladas no se borran; se marca `estado = 'ANULADO'`.
- **Trazabilidad:** Se guarda `motivo_anulacion`, `usuario_anulo_id` y `fecha_anulacion`.
- **Modal obligatorio:** Al anular se debe indicar el motivo (requerido para auditoría).
- **Reporte:** Documentos Anulados muestra motivo, usuario y fecha de anulación.

### Pendiente (integración MH)
- Transmitir **Evento de Invalidación** al MH dentro del plazo legal.
- Consultar normativa vigente para plazos de invalidación.

---

## 2. Libro de Ventas

### Implementado
- **Libro de IVA:** Ventas gravadas, IVA 13%, Retención IVA 1%.
- **Exportaciones:** Excel, CSV (UTF-8 con BOM, separador `;`), PDF.
- **CSV:** Formato adecuado para conciliación con DTE transmitidos.

### Recomendación
- Cotejar el Libro de IVA exportado con los DTE transmitidos al MH.
- Verificar que coincidan códigos de generación y totales.

---

## 3. DTE en Contingencia

### Estructura preparada
- Campo `estado_dte` en ventas: `RESPALDO` | `CONTINGENCIA` | `PENDIENTE_TRANSMISION` | `TRANSMITIDO`.
- Campos `codigo_generacion` y `numero_control` para trazabilidad con MH.

### Flujo futuro (cuando se integre con MH)
1. Si no hay conexión al MH → emitir como `CONTINGENCIA`.
2. Guardar en cola con `estado_dte = 'PENDIENTE_TRANSMISION'`.
3. Proceso automático o manual que transmita cuando se restaure la conexión.

---

## 4. Validaciones

### Implementado
- **NIT:** 14 dígitos (cliente tipo NIT).
- **NRC:** 6-7 dígitos (cliente tipo NRC).

---

## 5. Ejecutar migraciones

```bash
python scripts/alter_retencion_iva_gran_contribuyente.py
python scripts/alter_ventas_auditoria_dte.py
```

---

## 6. Recepción de Compras (DTE del proveedor)

### Implementado
- **Cargar DTE:** Módulo en Compras → Cargar DTE. Sube el archivo JSON que el proveedor envía por correo.
- **Extracción automática:** Lee `codigoGeneracion` (UUID), `selloRecepcion`, emisor, receptor, items y totales.
- **Validación MH:** Enlace a https://portaldgii.mh.gob.sv/ssc/consulta/fe?codigoGeneracion=XXX para verificar que el documento es legal y no ha sido invalidado.
- **Registrar compra:** Botón para registrar la compra desde el DTE (busca proveedor por NIT o crea uno, agrega items que coincidan por código o nombre).
- **Trazabilidad:** Compras guardan `codigo_generacion` y `sello_recepcion` para auditoría.

### Flujo
1. Proveedor envía correo con JSON adjunto.
2. Usuario va a Compras → Cargar DTE → selecciona archivo.
3. Sistema muestra datos extraídos y enlace "Validar en MH".
4. Usuario verifica en el portal del MH.
5. Usuario hace clic en "Registrar compra desde DTE".

---

## 7. Integración con Ministerio de Hacienda

Para transmisión electrónica al MH se requiere:
- Certificado digital (Firma electrónica).
- Credenciales del proveedor de facturación autorizado o API MH.
- Implementar Evento de Invalidación cuando se anule un DTE ya transmitido.
