@echo off
chcp 65001 >nul
REM Abre el POS en produccion. Para icono en el escritorio ejecute crear_acceso_directo_caja.bat
call "%~dp0iniciar_chrome_pos_impresion_silenciosa.bat"
exit /b %ERRORLEVEL%
