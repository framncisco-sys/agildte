@echo off
chcp 65001 >nul
title AgilDTE - Crear acceso directo
echo.
echo  Creando acceso directo en el Escritorio con icono AgilDTE...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_acceso_directo_caja.ps1"
if errorlevel 1 (
  echo.
  echo  [ERROR] No se pudo crear el acceso directo.
  pause
  exit /b 1
)
echo.
pause
exit /b 0
