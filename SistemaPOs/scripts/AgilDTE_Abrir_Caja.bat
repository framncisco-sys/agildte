@echo off
chcp 65001 >nul
REM Copie SOLO este archivo al escritorio de la PC de caja (USB, correo, etc.).
REM No requiere el proyecto ni Docker: el POS vive en https://agildte.com
REM Requisitos en la caja: Google Chrome + internet + impresora EPSON predeterminada.

set "POS_URL=https://agildte.com/pos/ventas_pos"
set "CHROME="

for %%P in (
  "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
  "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
  "%LocalAppData%\Google\Chrome\Application\chrome.exe"
) do if exist %%~P set "CHROME=%%~P"

if not defined CHROME (
  echo Instale Google Chrome en esta PC.
  pause
  exit /b 1
)

start "" "%CHROME%" --kiosk-printing --app="%POS_URL%"
exit /b 0
