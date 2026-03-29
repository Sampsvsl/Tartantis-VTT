@echo off
:: ═══════════════════════════════════════════════════════════════════
::  Tartantis VTT — Build Windows (.exe)
::  Gera TartantisVTT.exe usando PyInstaller
::
::  Pre-requisitos: pip install pyinstaller
::  Uso: Clique duas vezes neste arquivo
:: ═══════════════════════════════════════════════════════════════════

echo.
echo   Tartantis VTT - Build Windows EXE
echo   -----------------------------------
echo.

python --version >/dev/null 2>&1
if errorlevel 1 ( echo ERRO: Python nao encontrado. & pause & exit /b 1 )

python -m PyInstaller --version >/dev/null 2>&1
if errorlevel 1 ( echo Instalando PyInstaller... & pip install pyinstaller )

cd /d "%~dp0"
set WIN_DIR=%~dp0
set ROOT_DIR=%WIN_DIR%..

set ICON_OPT=
if exist "%ROOT_DIR%\assets\icon.ico" set ICON_OPT=--icon="%ROOT_DIR%\assets\icon.ico"

python -m PyInstaller ^
  --onefile --noconsole ^
  --name "TartantisVTT" ^
  %ICON_OPT% ^
  --add-data "%ROOT_DIR%\app;app" ^
  --add-data "%ROOT_DIR%\core;core" ^
  --distpath "%ROOT_DIR%\dist" ^
  --workpath "%WIN_DIR%\build-tmp" ^
  --specpath "%WIN_DIR%." ^
  "%WIN_DIR%launcher.py"

if exist "%ROOT_DIR%\dist\TartantisVTT.exe" (
  echo [OK] Gerado: dist\TartantisVTT.exe
) else ( echo ERRO: Falha na geracao. )
pause
