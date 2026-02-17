# Servicios de Facturación Electrónica

## FacturacionService

Servicio robusto para procesar facturas electrónicas con el Ministerio de Hacienda de El Salvador.

### Características

- ✅ Integración completa con `DTEGenerator` (sin código duplicado)
- ✅ Usa credenciales desde el modelo `Empresa` (no hardcodeadas)
- ✅ Manejo robusto de errores con excepciones personalizadas
- ✅ Logging completo para debugging
- ✅ Soporte para ambientes PRUEBAS y PRODUCCION
- ✅ Actualización automática del estado de la venta

### Uso Básico

```python
from api.models import Empresa, Venta
from api.services import FacturacionService

# Obtener la empresa
empresa = Empresa.objects.get(id=1)

# Crear el servicio
servicio = FacturacionService(empresa)

# Obtener la venta a procesar
venta = Venta.objects.get(id=123)

# Procesar la factura completa
try:
    resultado = servicio.procesar_factura(venta)
    
    if resultado['exito']:
        print(f"✅ Factura procesada exitosamente")
        print(f"Sello: {resultado['sello_recibido']}")
        print(f"Código: {resultado['codigo_generacion']}")
    else:
        print(f"⚠️ Factura rechazada: {resultado['mensaje']}")
        
except FacturacionServiceError as e:
    print(f"❌ Error: {e}")
```

### Métodos Disponibles

#### `obtener_token() -> str`
Obtiene el token de autenticación de MH usando las credenciales de la empresa.

#### `firmar_dte(json_dte: dict) -> str`
Firma digitalmente un documento DTE usando el certificado de la empresa.

#### `enviar_dte(dte_firmado: str, codigo_generacion: str, tipo_dte: str) -> dict`
Envía el DTE firmado a MH y retorna la respuesta.

#### `procesar_factura(venta: Venta) -> dict`
Método principal que orquesta todo el proceso:
1. Genera el JSON DTE usando `DTEGenerator`
2. Firma el documento
3. Envía a MH
4. Actualiza el estado de la venta

### Configuración Requerida en Empresa

El modelo `Empresa` debe tener configurados:

- `user_api_mh`: Usuario NIT/DUI para autenticación
- `clave_api_mh`: Contraseña de la API
- `ambiente`: 'PRUEBAS' o 'PRODUCCION'
- `archivo_certificado`: Archivo .crt para firma
- `clave_certificado`: Contraseña del certificado
- `cod_actividad`: Código de actividad económica (opcional)
- `desc_actividad`: Descripción de actividad (opcional)

### Excepciones

- `FacturacionServiceError`: Excepción base
- `AutenticacionMHError`: Error en autenticación
- `FirmaDTEError`: Error en firma digital
- `EnvioMHError`: Error al enviar a MH

### Configuración de Settings

Opcionalmente, puedes configurar la URL del firmador en `settings.py`:

```python
DTE_FIRMADOR_URL = 'http://localhost:8113/firmardocumento/'
```

Si no se configura, usa el valor por defecto: `http://localhost:8113/firmardocumento/`
