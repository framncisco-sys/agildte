@echo off
chcp 65001 >nul
title AgilDTE - Punto de venta
color 0B
REM ---------------------------------------------------------------------------
REM POS AgilDTE: Chrome con impresion silenciosa + pantalla de inicio con logo.
REM Mantenga en la misma carpeta: agildte_pos_logo.png y pos_splash.ps1
REM ---------------------------------------------------------------------------
set "SCRIPT_DIR=%~dp0"
set "POS_URL=https://agildte.com/pos/ventas_pos"
set "CHROME="
set "POS_PROFILE=%LocalAppData%\AzDigital_POS_Chrome"
set "LOGO=%SCRIPT_DIR%agildte_pos_logo.png"
set "SPLASH=%SCRIPT_DIR%pos_splash.ps1"

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
  echo.
  echo   [ERROR] No se encontro Google Chrome.
  echo.
  pause
  exit /b 1
)

cls
echo.
echo   ========================================
echo        AgilDTE - Punto de venta
echo   Facturacion electronica simple y rapida
echo   ========================================
echo.
echo   URL: %POS_URL%
echo   Impresion silenciosa: activada
echo.

if exist "%LOGO%" if exist "%SPLASH%" (
  start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%SPLASH%" -LogoPath "%LOGO%" -Seconds 2
) else (
  echo   [Aviso] Coloque agildte_pos_logo.png junto a este .bat para ver el logo.
  echo.
  timeout /t 2 /nobreak >nul
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
