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

:: CHECK FOR CONDA (Miniforge/Anaconda)
where conda >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Conda detectado. Usando metodo robusto (recomendado).
    
    REM Determine if using mamba (usually faster/better in Miniforge)
    set "CONDA_EXE=conda"
    where mamba >nul 2>&1
    if !errorlevel! equ 0 set "CONDA_EXE=mamba"

    echo [INFO] Usando: !CONDA_EXE!

    if not exist "%VENV_NAME%" (
        echo [INFO] Creando entorno Conda local...
        REM Create local env using --prefix (install into folder "env_climate_app" instead of global envs)
        call !CONDA_EXE! create --prefix "./%VENV_NAME%" python=3.11 -y
        if errorlevel 1 goto error_install

        echo [INFO] Instalando librerias pesadas via Conda-Forge...
        REM Install heavy geolibs via conda (no compilation needed)
        call !CONDA_EXE! install --prefix "./%VENV_NAME%" -c conda-forge geopandas rioxarray xarray netCDF4 matplotlib scipy numpy python-docx -y
        if errorlevel 1 goto error_install
        
        echo [INFO] Instalando librerias restantes via Pip...
        call "%VENV_NAME%\python.exe" -m pip install -r requirements.txt
    ) else (
        echo [INFO] Entorno Conda encontrado en ./%VENV_NAME%
        echo [INFO] Verificando/Actualizando via Pip...
        REM We use the python executable directly from the local env
        call "%VENV_NAME%\python.exe" -m pip install -r requirements.txt
    )

) else (
    echo [INFO] Conda NO detectado. Usando Python estandar (Pip).
    echo [WARNING] Si esto falla con errores de "Build", por favor instale Miniforge.

    if not exist "%VENV_NAME%" (
        echo [INFO] Configurando entorno virtual standard...
        python -m venv "%VENV_NAME%"
        if errorlevel 1 goto error_install
        
        call "%VENV_NAME%\Scripts\activate.bat"
        
        echo [INFO] Actualizando PIP (CRITICO para evitar errores de compilacion)...
        python -m pip install --upgrade pip
        
        echo [INFO] Intentando instalar wheel de Numpy primero...
        python -m pip install "numpy<2.0.0" --only-binary :all:
        
        echo [INFO] Instalando resto de librerias...
        pip install -r requirements.txt
        if errorlevel 1 goto error_install
    ) else (
        echo [INFO] Entorno VENV encontrado.
        call "%VENV_NAME%\Scripts\activate.bat"
        pip install -r requirements.txt
        if errorlevel 1 goto error_install
    )
)

goto launch

:error_install
echo.
echo [ERROR] Fallo la instalacion.
echo ---------------------------------------------------------
echo POSIBLE SOLUCION:
echo 1. Si usa Windows, instale MINIFORGE (ver manual).
echo 2. Asegurese de marcar "Add to PATH" al instalarlo.
echo 3. Intente de nuevo.
echo ---------------------------------------------------------
pause
exit /b 1

:launch

echo.
echo [INFO] Lanzando aplicacion...
echo Si el navegador no se abre, vaya a: http://localhost:8501
echo Presione Ctrl+C para detener.
echo.

REM FIX: Clear system environment variables that might conflict (PostgreSQL/PostGIS)
set PROJ_LIB=
set GDAL_DATA=

REM Launch Streamlit
if exist "%VENV_NAME%\python.exe" (
    REM Conda/Venv local path style
    "%VENV_NAME%\python.exe" -m streamlit run app.py
) else (
    :: Fallback to activated path
    python -m streamlit run app.py
)

echo.
echo [INFO] Streamlit termino o se cerro.
pause
