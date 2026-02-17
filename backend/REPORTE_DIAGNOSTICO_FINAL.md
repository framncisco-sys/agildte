# DIAGNÓSTICO COMPLETO - Backend Django / DTE MH

**Fecha:** 6 de febrero de 2026  
**Alcance:** Estructura, código crítico DTE-03, smoke test, veredicto.

---

## 1. ESCANEO DE ESTRUCTURA

### Settings y manage.py
| Elemento | Resultado |
|----------|-----------|
| **Settings activo** | `sistema_contable.settings` (ruta real: `backend/sistema_contable/settings.py`) |
| **manage.py** | Apunta correctamente a `sistema_contable.settings` (línea 9) |
| **¿Existe `proyecto/settings.py`?** | **No.** No existe carpeta `proyecto` en el repo. |
| **¿Existe `backend/settings.py`?** | **No.** Solo existe `backend/sistema_contable/settings.py`. |

### Scripts con referencias incorrectas
- **`generar_evidencia_mh.py`**: usa `proyecto.settings` y `FacturacionService()` sin argumentos; llama a `servicio._get_generator(...)` que **no existe** en `FacturacionService`. **Script roto.**
- **`generar_evidencia_final.py`**: intenta `proyecto.settings` y `backend.settings` (ninguno existe); usa `FacturacionService()` sin args y `_get_generator()`; filtra por `cliente__es_contribuyente` (el modelo tiene `tipo_cliente`, no `es_contribuyente`). **Script roto.**
- **`auditor_mh.py`**: fallback a `backend.settings` en caso de error (ese módulo no existe); el resto usa `sistema_contable.settings` correctamente.

### Duplicados de código crítico
| Archivo | ¿Existe más de una vez? | Ubicación |
|---------|-------------------------|-----------|
| `dte_generator.py` | **No.** Una sola versión. | `backend/api/dte_generator.py` |
| `facturacion_service.py` | **No.** Una sola versión. | `backend/api/services/facturacion_service.py` |

**Conclusión estructura:** El núcleo Django está bien definido (un solo settings, un solo generador, un solo servicio). La confusión viene de scripts antiguos que apuntan a módulos inexistentes y a una API que ya no existe (`_get_generator`, `FacturacionService()` sin empresa).

---

## 2. ANÁLISIS DE CÓDIGO CRÍTICO (DTE-03)

### Clase que genera el JSON
- **Clase:** `DTEGenerator` en `api/dte_generator.py` (no en `api/services/` ni `api/utils/`).
- **Uso:** `FacturacionService.procesar_factura(venta)` instancia `DTEGenerator(venta)` y llama a `generar_json(ambiente=...)`.

### ¿Versión 1 o Versión 3?
- **El código principal está configurado para Versión 1.**
- En `dte_generator.py` (aprox. líneas 320-325):
  - `version_dte = 1  # Siempre versión 1 para ambos tipos de DTE`
  - `identificacion["version"] = int(version_dte)`
- En `cuerpoDocumento`, cada ítem incluye **`ivaItem`** (típico de V1). En V3 (Catálogo 2025) los ítems no llevan `ivaItem`, solo `ventaGravada` y `tributos: ["20"]`.

### Lógica hardcodeada vs modelos
- **Correlativos:** Usa modelo `Correlativo` y `CorrelativoDTE.obtener_siguiente_correlativo()` (empresa, tipo DTE, año). Correcto.
- **Emisor/Receptor:** Datos desde modelos `Empresa` y `Cliente` (Venta.cliente). Correcto.
- **Montos:** Cuerpo y resumen se calculan desde `DetalleVenta` y `Venta` (venta_gravada, debito_fiscal, etc.). Correcto.
- **Parches de diagnóstico:** En `facturacion_service.py` hay varios `print()` de DEBUG (identificación, receptor, JSON generado). Son útiles para soporte pero ensucian la salida en producción.

**Conclusión código:** La lógica está bien apoyada en modelos y es coherente. El único “parche” estructural es la versión fija a **V1** cuando MH (y tu necesidad actual) piden **V3**.

---

## 3. PRUEBA DE HUMO (Smoke Test)

**Script:** `diagnostico_final.py` (en `backend/`).

**Qué hace (solo clases del proyecto):**
1. Django setup con `sistema_contable.settings`.
2. `Empresa.objects.first()`, `Venta` CCF (o última venta).
3. `FacturacionService(empresa)`, `DTEGenerator(venta).generar_json(ambiente=...)`, `servicio.firmar_dte(json_dte)`.
4. Guarda el envelope en `DIAGNOSTICO_SMOKE_TEST_RESULTADO.json`.

**Resultado de la ejecución:**
- Empresa y Venta obtenidas correctamente.
- JSON generado con **version=1**, **tipoDte=03**.
- Documento firmado (JWS) obtenido correctamente.
- Archivo de resultado generado.

**Conclusión:** El sistema (generador + firma) **funciona** usando solo las clases oficiales del proyecto, sin JSON manual en el script.

---

## 4. REPORTE FINAL (Formato solicitado)

### Estado del Entorno
**Semáforo: 🟡 AMARILLO**

| Aspecto | Estado |
|---------|--------|
| **Rutas / Settings** | 🟢 Un solo settings real (`sistema_contable.settings`). 🟡 Varios scripts siguen usando `proyecto.settings` o `backend.settings` (inexistentes). |
| **Venv** | 🟢 Entorno virtual en `backend/venv`; `manage.py check` y smoke test funcionan. |
| **Docker** | 🟢 No se usa en el repo (Procfile para despliegue tipo Heroku). Sin conflictos. |

### Calidad del Código DTE
**Semáforo: 🟡 AMARILLO**

- **¿Limpio o lleno de parches?**  
  El núcleo (`dte_generator.py`, `facturacion_service.py`) está ordenado y usa bien los modelos. Hay parches localizados: `print()` de DEBUG en `facturacion_service` y **versión fija a V1** en el generador.
- **¿Genera V1 o V3?**  
  **Genera V1** (version=1, ivaItem en ítems). Para MH (Catálogo 2025) necesitas **V3** (sin ivaItem en ítems; IVA en resumen).

### Resultado de la Prueba
- **¿Logró generar el JSON firmado automáticamente?**  
  **Sí.** El smoke test generó JSON (V1) y obtuvo el JWS usando solo `DTEGenerator` y `FacturacionService`.
- **¿Qué error dio?**  
  **Ninguno.** La prueba terminó en éxito y generó `DIAGNOSTICO_SMOKE_TEST_RESULTADO.json`.

### VEREDICTO

**OPCIÓN A: RESCATE.**

**Justificación breve:**

1. **Núcleo sólido:** Un solo `settings`, un solo `dte_generator`, un solo `facturacion_service`. No hay duplicados ni rutas “mágicas” en el código crítico.
2. **Modelos y flujo correctos:** Emisor, receptor, correlativos y montos se apoyan en modelos; el flujo generar → firmar funciona con las clases oficiales.
3. **La “suciedad” es acotada:**  
   - Scripts de evidencia (`generar_evidencia_mh.py`, `generar_evidencia_final.py`) rotos por referencias a módulos inexistentes y API antigua.  
   - Referencias a `proyecto.settings` / `backend.settings` en esos scripts (y fallback en `auditor_mh.py`).  
   - Generador fijado a **V1** cuando el estándar actual es **V3**.
4. **No hace falta reinicio limpio:** La estructura del backend es reconocible y estable. Un nuevo proyecto Django y migrar modelos/vistas sería más costoso que limpiar y actualizar lo que ya funciona.

**Recomendaciones concretas:**

- **Rescate inmediato:**  
  - Borrar o archivar scripts que no se usen (p. ej. `generar_evidencia_mh.py`, `generar_evidencia_final.py` si ya no son necesarios).  
  - Unificar todos los scripts que usen Django a `sistema_contable.settings` y a `FacturacionService(empresa)` (nunca `FacturacionService()` ni `_get_generator`).  
  - Opcional: reducir o condicionar los `print()` de DEBUG en `facturacion_service.py` (por nivel de log o variable de entorno).

- **Siguiente paso (refactorización acotada):**  
  Actualizar `dte_generator.py` para soportar **Versión 3** (Catálogo 2025): `identificacion.version = 3`, ítems sin `ivaItem`, IVA solo en resumen. Puedes usar como referencia el JSON generado por `force_dte_v3.py` (que ya construye V3 manualmente) para alinear el generador oficial sin reescribir todo el proyecto.

---

*Documento generado por diagnóstico automatizado (diagnostico_final.py) y revisión manual de estructura y código.*
