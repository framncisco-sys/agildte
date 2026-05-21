@echo off
chcp 65001 >nul
REM ---------------------------------------------------------------------------
REM POS AzDigital: Chrome con impresion silenciosa (sin dialogo "Imprimir").
REM
REM IMPORTANTE: use SIEMPRE este acceso directo en la caja. Si abre Chrome normal
REM y luego este .bat, Windows puede reutilizar Chrome SIN --kiosk-printing.
REM Este script usa un perfil propio (--user-data-dir) para evitar eso.
REM
REM Requisitos:
REM   1) Google Chrome instalado
REM   2) EPSON TM-T20II (u otra) como impresora PREDETERMINADA en Windows
REM   3) Una vez: imprimir ticket de prueba y guardar preferencias 80mm
REM
REM URL por defecto: produccion. Desarrollo:
REM   iniciar_chrome_pos_impresion_silenciosa.bat local
REM   iniciar_chrome_pos_impresion_silenciosa.bat "http://localhost:8080/pos/ventas_pos"
REM ---------------------------------------------------------------------------
set "POS_URL=https://agildte.com/pos/ventas_pos"
set "CHROME="
set "POS_PROFILE=%LocalAppData%\AzDigital_POS_Chrome"

if /I "%~1"=="local" (
  set "POS_URL=http://localhost/pos/ventas_pos"
) else if /I "%~1"=="localhost" (
  set "POS_URL=http://localhost/pos/ventas_pos"
) else if not "%~1"=="" (
  set "POS_URL=%~1"
)

for %%P in (
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do (
  if exist %%~P set "CHROME=%%~P"
)

if not defined CHROME (
  echo [ERROR] No se encontro chrome.exe. Instale Google Chrome.
  pause
  exit /b 1
)

echo.
echo  POS - impresion silenciosa
echo  URL: %POS_URL%
echo  Perfil Chrome: %POS_PROFILE%
echo  Impresora: predeterminada de Windows
echo.
echo  Si aun sale el cuadro "Imprimir":
echo    - Cierre TODAS las ventanas de este POS (Alt+F4) y vuelva a abrir SOLO con este .bat
echo    - No abra agildte.com desde otro acceso directo de Chrome
echo    - Confirme impresora predeterminada en Configuracion de Windows
echo.

REM Perfil aislado: garantiza que --kiosk-printing se aplique (no mezcla con Chrome personal).
REM --disable-print-preview: en muchas versiones evita la vista previa antes de imprimir.
start "" "%CHROME%" ^
  --user-data-dir="%POS_PROFILE%" ^
  --kiosk-printing ^
  --disable-print-preview ^
  --no-first-run ^
  --no-default-browser-check ^
  --disable-session-crashed-bubble ^
  --app="%POS_URL%"

exit /b 0
