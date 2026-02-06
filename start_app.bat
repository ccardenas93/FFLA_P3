@echo off
setlocal

echo ==========================================
echo    Iniciando Web App de Analisis Climatico
echo ==========================================

:: Nombre del entorno virtual
set "VENV_NAME=env_climate_app"

:: Verificar si existe Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado. Por favor instale Python 3.10+ y agreguelo al PATH.
    pause
    exit /b 1
)

:: Verificar/Crear entorno virtual
if not exist "%VENV_NAME%" (
    echo [INFO] Configurando entorno por primera vez (esto puede tardar)...
    python -m venv %VENV_NAME%
    
    :: Activar y actualizar pip
    call %VENV_NAME%\Scripts\activate
    python -m pip install --upgrade pip
    
    :: Instalar dependencias
    echo [INFO] Instalando librerias necesarias...
    pip install -r requirements.txt
    
    if %errorlevel% neq 0 (
        echo [ERROR] Fallo la instalacion de dependencias. Verifique su conexion.
        pause
        exit /b 1
    )
) else (
    echo [INFO] Entorno encontrado. Verificando dependencias...
    call %VENV_NAME%\Scripts\activate
    pip install -r requirements.txt
)

:: Ejecutar la app
echo [INFO] Lanzando aplicacion...
echo Si el navegador no se abre, vaya a: http://localhost:8501
echo Presione Ctrl+C para detener.

streamlit run app.py

pause
