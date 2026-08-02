# Resumen de cambios — AgilDTE (para presentar a clientes)
# Fecha meta: 01/08/2026

## Resumen ejecutivo (1 minuto)

Actualizamos AgilDTE a la normativa MH vigente (schemas v2/v4), mejoramos Factura a Consumidor Final, Notas de Crédito/Débito, ubicación (departamentos/municipios), WhatsApp centralizado e invalidación. Los DTE antiguos aceptados por Hacienda **no se regeneran**: se conservan tal como fueron firmados.

---

## Qué cambia para el usuario

### 1. Factura Consumidor Final (DTE-01)
- Si deja vacío el **nombre**, el sistema pone automáticamente **Consumidor Final**.
- La **ubicación del cliente es opcional** (departamento, municipio, distrito y dirección). Si no se llena, el DTE va sin dirección.

### 2. Ubicación MH (catálogo corregido)
- Se corrigió el catálogo oficial: **12 = San Miguel**, **13 = Morazán** (antes estaban intercambiados).
- Al jalar un CCF hacia Nota de Crédito/Débito, ahora sí se cargan departamento, municipio y distrito del documento.
- En servidor se debe ejecutar una corrección automática de clientes/ventas afectados (comando abajo).
- **Recomendación a usuarios:** al abrir clientes de San Miguel, confirmar que el departamento diga San Miguel (no Morazán) y guardar si hace falta.

### 3. Notas de Crédito (05) y Débito (06)
- Actualizadas al schema MH **v4**.
- Deben referenciar siempre el CCF/documento original.
- Corrección de cálculo de IVA en resumen para evitar rechazos de Hacienda.

### 4. Invalidación de documentos
- Corregido envío de **teléfono y correo** del receptor (obligatorios para MH), también en CF sin datos de contacto.

### 5. WhatsApp
- Número centralizado AgilDTE (no credenciales Meta por empresa).
- El módulo se habilita por empresa (premium); el envío pide el teléfono al usuario.

### 6. Documentos históricos
- Facturas ya **procesadas/aceptadas** no se rehacen con la lógica nueva.
- Descarga de JSON/PDF usa el documento original firmado.

### 7. Tipos aún no habilitados
- DTE 07 / 08 / 09 / 15 quedan **bloqueados** hasta completar su migración MH (no se sustituyen por CCF).

---

## Qué debe hacer el equipo al subir a servidor

1. Deploy del backend + frontend.
2. Ejecutar corrección de departamentos San Miguel/Morazán:
   ```bash
   python manage.py corregir_depto_san_miguel_morazan --dry-run
   python manage.py corregir_depto_san_miguel_morazan --apply
   ```
3. Aviso corto a usuarios (texto sugerido):
   > Actualizamos el catálogo de ubicación MH. Si su cliente es de San Miguel, confirme en la ficha que el departamento diga **San Miguel** (no Morazán) y que municipio/distrito coincidan.
4. Pruebas rápidas en ambiente de Hacienda:
   - CF sin nombre / sin dirección
   - CCF
   - NC y ND referenciando un CCF
   - Invalidar un CF

---

## Beneficios para el cliente

- Menos rechazos de Hacienda por catálogos y schemas desactualizados.
- CF más ágil (menos campos obligatorios).
- NC/ND alineadas a la normativa actual.
- WhatsApp unificado y simple.
- Seguridad de no alterar facturas históricas ya aceptadas.
