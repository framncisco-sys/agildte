# Opciones para la firma de DTE (Ministerio de Hacienda - El Salvador)

Para emitir facturas electrónicas hay que **firmar el JSON del DTE** antes de enviarlo a MH. Estas son las opciones que tienes.

---

## Opción 1: Firmador interno (recomendada) — ya implementada

**Qué es:** La firma se hace dentro del backend Django con Python. No hace falta ningún contenedor ni servicio externo de firmador.

**Ventajas:**
- No dependes de imágenes Docker ni de terceros.
- El servidor funciona aunque no tengas el contenedor `firmador`.
- Usa el mismo certificado MH (archivo `.crt` en formato XML) que subes en la empresa.

**Cómo activarla:** Viene activada por defecto. En el servidor, en tu `.env`:

```env
USE_INTERNAL_FIRMADOR=true
```

(No hace falta poner nada si usas el default.)

**Requisitos:** En el backend están las dependencias `cryptography` y `jwcrypto`. El certificado de la empresa debe ser el formato XML de MH (el que descargas desde el portal de MH).

---

## Opción 2: Firmador externo (contenedor propio)

**Qué es:** Un servicio aparte (por ejemplo un contenedor) que expone `POST /firmardocumento/` y devuelve el JWS.

**Cuándo usarla:** Si prefieres usar la solución en Go u otra que ya tengas.

**Pasos resumidos:**
1. Clonar un proyecto que exponga esa API (por ejemplo [GoFirmadorDTE-SV](https://github.com/snaven10/GoFirmadorDTE-SV)).
2. Construir la imagen en el servidor:  
   `docker build -t firmador-local:latest .`
3. En `docker-compose.prod.yml`: servicio firmador con `image: firmador-local:latest` y sin `profiles` (o con el profile que uses).
4. En `.env`:  
   `USE_INTERNAL_FIRMADOR=false`  
   `FIRMADOR_URL=http://firmador:8113/`

---

## Opción 3: Servicio de firma de terceros

**Qué es:** Un proveedor (SaaS) que ofrece API de firma de DTE para MH.

**Cuándo usarla:** Si contratas un servicio tipo FELSIVAR, Smart DTE, etc., que te den un endpoint para firmar.

**Qué harías:** Cambiar el backend para que, en lugar de llamar al firmador interno o al contenedor, llame a la API del tercero (adaptando request/response si hace falta). Se mantendría `USE_INTERNAL_FIRMADOR=false` y la URL del firmador apuntaría al servicio del proveedor.

---

## Resumen

| Opción              | ¿Necesitas contenedor firmador? | ¿Qué hacer en producción?                    |
|---------------------|----------------------------------|----------------------------------------------|
| 1. Interno (Python)| No                               | `USE_INTERNAL_FIRMADOR=true` (default)       |
| 2. Externo (Go, etc.) | Sí (construir imagen en servidor) | `USE_INTERNAL_FIRMADOR=false`, montar firmador |
| 3. Terceros         | No (API externa)                 | Integrar su API en el backend                |

Recomendación: usar **Opción 1 (firmador interno)** para que el servidor funcione y puedas emitir facturas sin depender del contenedor del firmador.
