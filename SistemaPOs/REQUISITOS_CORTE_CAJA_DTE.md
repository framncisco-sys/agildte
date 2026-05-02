# Requisitos de Corte de Caja bajo Facturación Electrónica (DTE) — El Salvador

**Programador:** Oscar Amaya Romero  
**Fuente:** Normativa MH y buenas prácticas de cuadre de caja

---

## 1. Reporte de Corte de Caja (X o Z)

Al final del turno, el cajero necesita un documento físico o digital que resuma todo lo operado.

### 1.1 Ventas por Tipo de DTE

| Código | Tipo | Descripción |
|--------|------|-------------|
| 01 | Factura Consumidor Final | Total facturas emitidas |
| 03 | Crédito Fiscal | Total CCF |
| 05 | Nota de Crédito | Resta del total (devoluciones) |

### 1.2 Ventas por Método de Pago

- **Efectivo:** Dinero físico que debe estar en la gaveta
- **Tarjeta (Crédito/Débito):** Suma de los vouchers del POS
- **Transferencia/Bitcoin:** Pagos confirmados por app

### 1.3 Impuestos Detallados

- **IVA cobrado (13%):** Del total de ventas gravadas
- **Retenciones (1%):** IVA retenido en ventas a Gran Contribuyente

---

## 2. Comprobante de Invalidación (Anulaciones)

Si se invalida un DTE:

- El sistema debe imprimir un **Comprobante de Invalidación**
- Debe citar el **codigoGeneracion** del DTE original
- **Contablemente:** El cajero entrega este papel para justificar por qué hay una venta en el sistema cuyo dinero no está en la caja

---

## 3. Sujeto Excluido (DTE 14) — Si aplica

Compras a personas sin IVA (ej: pago de limpieza a persona natural):

- Cuenta como **salida de efectivo**
- El cajero debe entregar el comprobante impreso para justificar el egreso

---

## 4. Tabla CierreCaja (Base de Datos)

| Campo | Propósito |
|-------|-----------|
| monto_apertura | Con cuánto dinero inició el turno |
| ventas_efectivo | Suma de DTEs pagados en efectivo |
| ventas_tarjeta | Suma de DTEs pagados con POS |
| salidas_efectivo | Egresos (sujeto excluido, gastos menores, etc.) |
| monto_esperado | Apertura + Ventas Efectivo - Salidas |
| monto_real | Lo que el cajero dice que contó |
| diferencia | Sobrante o faltante |

---

## 5. Entregables al Contador (fin de mes)

- **Libro de Ventas a Consumidor Final:** Resumen diario de Facturas (01)
- **Libro de Ventas a Contribuyentes:** Listado detallado de cada CCF (03) con NIT/NRC
- **Archivo JSON/CSV de Anexos:** Formato para subir al portal MH

---

## 6. Cierre a Ciegas (Recomendación de seguridad) — IMPLEMENTADO ✅

**No permitir** que el cajero vea el "Monto Esperado" antes de ingresar cuánto dinero contó. Evita que los cajeros "ajusten" las cuentas para que siempre cuadre.

**Flujo:**
1. Cajero ingresa `monto_real` (lo que contó)
2. Sistema calcula y muestra diferencia
3. Recién entonces se revela el monto esperado

**Ruta:** `/cierre_caja` — Apertura y cierre a ciegas (menú Ventas)
