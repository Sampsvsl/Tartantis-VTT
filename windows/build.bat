@echo off
:: ═══════════════════════════════════════════════════════════════════
::  Tartantis VTT — Build Instalador Windows (.exe)
:: ═══════════════════════════════════════════════════════════════════

echo.
echo   Tartantis VTT - Build Windows Instalador
echo   ----------------------------------------
echo.

python --version >/dev/null 2>&1
if errorlevel 1 ( echo ERRO: Python nao encontrado. & pause & exit /b 1 )

python -m PyInstaller --version >/dev/null 2>&1
if errorlevel 1 ( echo Instalando PyInstaller... & pip install pyinstaller )

cd /d "%~dp0"
set WIN_DIR=%~dp0
set ROOT_DIR=%WIN_DIR%..
set TMP_DIR=%WIN_DIR%build-tmp

if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
mkdir "%TMP_DIR%"

set ICON_OPT=
if exist "%ROOT_DIR%\assets\icon.ico" set ICON_OPT=--icon="%ROOT_DIR%\assets\icon.ico"

echo [1/3] Compilando Engine (TartantisVTT.exe)...
python -m PyInstaller ^
  --onefile --noconsole ^
  --name "TartantisVTT" ^
  %ICON_OPT% ^
  --hidden-import=http.server ^
  --hidden-import=socketserver ^
  --hidden-import=secrets ^
  --hidden-import=xmlrpc.server ^
  --hidden-import=webbrowser ^
  --distpath "%TMP_DIR%\engine" ^
  --workpath "%TMP_DIR%\work" ^
  --specpath "%TMP_DIR%" ^
  "%WIN_DIR%launcher.py"
  
if not exist "%TMP_DIR%\engine\TartantisVTT.exe" (
    echo ERRO: Falha ao compilar Engine.
    pause
    exit /b 1
)

echo [2/3] Criando Payload (payload.zip)...
python "%WIN_DIR%zipper.py" "%ROOT_DIR%" "%TMP_DIR%\engine\TartantisVTT.exe" "%TMP_DIR%\payload.zip"
if not exist "%TMP_DIR%\payload.zip" (
    echo ERRO: Falha ao gerar payload.zip
    pause
    exit /b 1
)

echo [3/3] Compilando Instalador...
python -m PyInstaller ^
  --onefile --noconsole ^
  --name "Instalador_TartantisVTT" ^
  %ICON_OPT% ^
  --add-data "%TMP_DIR%\payload.zip;." ^
  --distpath "%ROOT_DIR%\dist" ^
  --workpath "%TMP_DIR%\work-installer" ^
  --specpath "%WIN_DIR%." ^
  "%WIN_DIR%installer.py"

if exist "%ROOT_DIR%\dist\Instalador_TartantisVTT.exe" (
  echo [OK] Gerado: dist\Instalador_TartantisVTT.exe
) else ( 
  echo ERRO: Falha na geracao do Instalador. 
)
pause
