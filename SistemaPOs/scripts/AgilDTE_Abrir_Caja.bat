@echo off
chcp 65001 >nul
title AgilDTE - Caja
REM Copie al escritorio de la PC de caja estos 3 archivos juntos:
REM   AgilDTE_Abrir_Caja.bat
REM   agildte_pos_logo.png
REM   pos_splash.ps1

set "SCRIPT_DIR=%~dp0"
set "POS_URL=https://agildte.com/pos/ventas_pos"
set "CHROME="
set "POS_PROFILE=%LocalAppData%\AzDigital_POS_Chrome"
set "LOGO=%SCRIPT_DIR%agildte_pos_logo.png"
set "SPLASH=%SCRIPT_DIR%pos_splash.ps1"

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

if exist "%LOGO%" if exist "%SPLASH%" (
  start "" powershell -NoProfile -ExecutionPolicy Bypass -File "%SPLASH%" -LogoPath "%LOGO%" -Seconds 2
)

start "" "%CHROME%" --user-data-dir="%POS_PROFILE%" --kiosk-printing --disable-print-preview --no-first-run --no-default-browser-check --app="%POS_URL%"
exit /b 0
