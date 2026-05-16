@echo off
:: ═══════════════════════════════════════════════════════════════════
::  Tartantis VTT — Build Windows Portatil (.zip)
:: ═══════════════════════════════════════════════════════════════════

echo.
echo   Tartantis VTT - Build Windows Portatil
echo   ----------------------------------------
echo.

python --version >nul 2>&1
if errorlevel 1 ( echo ERRO: Python nao encontrado. & exit /b 1 )

python -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
  echo Instalando PyInstaller...
  python -m pip install pyinstaller
)

cd /d "%~dp0"
set WIN_DIR=%~dp0
set ROOT_DIR=%WIN_DIR%..

echo Instalando dependencias Python...
python -m pip install -r "%ROOT_DIR%\requirements.txt" --quiet
set TMP_DIR=%WIN_DIR%build-tmp
set DIST_DIR=%ROOT_DIR%\dist
set STAGE_DIR=%TMP_DIR%\stage
set ZIP_PATH=%DIST_DIR%\TartantisVTT-Windows-Portable.zip

if exist "%TMP_DIR%" rmdir /s /q "%TMP_DIR%"
if exist "%ZIP_PATH%" del /f /q "%ZIP_PATH%"
mkdir "%TMP_DIR%"
mkdir "%STAGE_DIR%"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

set ICON_OPT=
if exist "%ROOT_DIR%\assets\icon.ico" set ICON_OPT=--icon="%ROOT_DIR%\assets\icon.ico"

echo [1/3] Compilando launcher em modo onedir...
python -m PyInstaller ^
  --noconfirm --clean --onedir --noconsole --noupx ^
  --name "TartantisVTT" ^
  %ICON_OPT% ^
  --distpath "%TMP_DIR%\engine" ^
  --workpath "%TMP_DIR%\work" ^
  --specpath "%TMP_DIR%" ^
  "%WIN_DIR%launcher.py"
  
   
if not exist "%TMP_DIR%\engine\TartantisVTT\TartantisVTT.exe" (
    echo ERRO: Falha ao compilar launcher.
     exit /b 1
 )
 
echo [2/3] Montando pacote portatil...
xcopy "%TMP_DIR%\engine\TartantisVTT\*" "%STAGE_DIR%" /E /I /Y >nul
xcopy "%ROOT_DIR%\app" "%STAGE_DIR%\app" /E /I /Y >nul
xcopy "%ROOT_DIR%\core" "%STAGE_DIR%\core" /E /I /Y >nul
if exist "%ROOT_DIR%\assets" xcopy "%ROOT_DIR%\assets" "%STAGE_DIR%\assets" /E /I /Y >nul
if exist "%ROOT_DIR%\VERSION" copy /Y "%ROOT_DIR%\VERSION" "%STAGE_DIR%\VERSION" >nul

if not exist "%STAGE_DIR%\TartantisVTT.exe" (
    echo ERRO: Falha ao montar pacote portatil.
     exit /b 1
 )
 
echo [3/3] Compactando ZIP de distribuicao...
powershell -NoProfile -Command "Compress-Archive -Path '%STAGE_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force"

if exist "%ZIP_PATH%" (
  echo [OK] Gerado: dist\TartantisVTT-Windows-Portable.zip
) else ( 
  echo ERRO: Falha na geracao do ZIP portatil.
)
