# Impresión silenciosa en caja (sin botón «Imprimir»)

## Por qué aparece el cuadro de diálogo

En Chrome, Edge o Firefox **no se puede** omitir el diálogo de impresión desde JavaScript en un uso normal. Es una regla de seguridad del navegador: ninguna página web puede enviar papel a la impresora sin que el usuario lo autorice (o sin un modo especial del navegador).

El flujo actual (`window.print()` + ventana emergente) es el estándar en aplicaciones web POS.

## Solución recomendada: Chrome con `--kiosk-printing`

En la **PC de la caja**, abra el POS con el script incluido:

```text
SistemaPOs/scripts/iniciar_chrome_pos_impresion_silenciosa.bat
```

(O cree un acceso directo en el escritorio que apunte a ese `.bat`.)

En la carpeta del script van **tres archivos** (para ver el logo al iniciar):

- `iniciar_chrome_pos_impresion_silenciosa.bat`
- `agildte_pos_logo.png`
- `pos_splash.ps1`

### Antes de usarlo

1. En **Windows → Configuración → Impresoras**, ponga la **EPSON TM-T20II** como impresora **predeterminada**.
2. Imprima **una vez** un ticket de prueba desde el diálogo normal y confirme que la Epson queda bien (tamaño 80 mm, sin márgenes excesivos). Chrome recordará esas opciones para el modo silencioso.
3. Abra el POS **solo** con el `.bat` (no abra Chrome normal y luego el POS).
4. El script usa un perfil dedicado (`%LocalAppData%\AzDigital_POS_Chrome`) para que `--kiosk-printing` no se pierda si ya tenía Chrome abierto.

### URL del POS

Por defecto el script abre **producción**:

`https://agildte.com/pos/ventas_pos`

Para desarrollo en su PC:

```bat
iniciar_chrome_pos_impresion_silenciosa.bat local
```

O con puerto distinto:

```bat
iniciar_chrome_pos_impresion_silenciosa.bat "http://localhost:8080/pos/ventas_pos"
```

La impresión silenciosa funciona igual en agildte.com y en localhost: depende del Chrome de la caja (`--kiosk-printing`), no del dominio.

### Comportamiento

- Al cobrar, la ventana emergente llama a `window.print()`.
- Con `--kiosk-printing`, Chrome envía el trabajo a la impresora predeterminada **sin mostrar** el cuadro «Imprimir / Cancelar» (puede haber un parpadeo muy breve).
- La ventana de ticket sigue cerrándose sola (`autoclose=1`).

### Salir

- Cierre la ventana de Chrome con **Alt+F4** o desde el administrador de tareas.

## Otras alternativas (más trabajo)

| Opción | Comentario |
|--------|------------|
| **QZ Tray** + impresora RAW | Control total ESC/POS; requiere instalar QZ y adaptar el POS. |
| **App de escritorio** (Electron) | Impresión nativa sin diálogo. |
| **Servicio Windows** que imprima PDF/HTML | El servidor genera el ticket y lo manda al spooler. |

## Si sigue apareciendo el cuadro «Imprimir»

1. Cierre **todas** las ventanas del POS (Alt+F4), no solo la pestaña del ticket.
2. Vuelva a abrir **solo** con el `.bat` del escritorio (no desde un icono de Chrome genérico).
3. Compruebe en `chrome://version` (en esa ventana del POS) que la línea **«Línea de comandos»** incluya `--kiosk-printing` y `--user-data-dir=...\AzDigital_POS_Chrome`.
4. Impresora **predeterminada** = EPSON TM-T20II en Windows.
5. En Chrome reciente, imprima **una vez** con el diálogo y pulse Imprimir; a veces guarda el destino para los siguientes tickets en ese perfil.

## Atajo mientras usa el diálogo normal

Si sigue con Chrome normal: al abrir el cuadro, **Enter** confirma «Imprimir» (la Epson ya suele estar seleccionada). No es automático, pero es un solo clic de teclado por venta.
