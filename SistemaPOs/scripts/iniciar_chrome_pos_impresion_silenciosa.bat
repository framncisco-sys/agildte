@echo off
chcp 65001 >nul
REM ---------------------------------------------------------------------------
REM POS AgilDTE: Chrome con impresion silenciosa (sin dialogo "Imprimir").
REM Use el acceso directo del escritorio (crear_acceso_directo_caja.bat) con el logo.
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

start "" "%CHROME%" ^
  --user-data-dir="%POS_PROFILE%" ^
  --kiosk-printing ^
  --disable-print-preview ^
  --no-first-run ^
  --no-default-browser-check ^
  --disable-session-crashed-bubble ^
  --app="%POS_URL%"

exit /b 0
