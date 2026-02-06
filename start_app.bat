@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Climate App Launcher
cd /d "%~dp0"

echo ==========================================
echo    Iniciando Web App de Analisis Climatico
echo ==========================================
echo Carpeta: %CD%
echo.

set "VENV_NAME=env_climate_app"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instale Python 3.10+ y agreguelo al PATH.
    pause
    exit /b 1
)

if not exist "requirements.txt" (
  echo [ERROR] No encuentro requirements.txt en: %CD%
  pause
  exit /b 1
)

if not exist "app.py" (
  echo [ERROR] No encuentro app.py en: %CD%
  pause
  exit /b 1
)

if not exist "%VENV_NAME%" (
    echo [INFO] Configurando entorno por primera vez...
    python -m venv "%VENV_NAME%"
    if errorlevel 1 (
      echo [ERROR] Fallo creando el entorno virtual.
      pause
      exit /b 1
    )

    call "%VENV_NAME%\Scripts\activate.bat"
    python -m pip install --upgrade pip
    echo [INFO] Instalando librerias necesarias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Fallo la instalacion de dependencias.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Entorno encontrado. Verificando dependencias...
    call "%VENV_NAME%\Scripts\activate.bat"
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Fallo instalando/verificando dependencias.
        pause
        exit /b 1
    )
)

echo.
echo [INFO] Lanzando aplicacion...
echo Si el navegador no se abre, vaya a: http://localhost:8501
echo Presione Ctrl+C para detener.
echo.

:: FIX: Clear system environment variables that might conflict (PostgreSQL/PostGIS)
set PROJ_LIB=
set GDAL_DATA=

python -m streamlit run app.py

echo.
echo [INFO] Streamlit termino o se cerro.
pause
