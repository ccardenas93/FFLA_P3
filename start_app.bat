@echo off
setlocal EnableExtensions EnableDelayedExpansion

title Climate App Launcher
cd /d "%~dp0"

echo ==========================================
echo    Iniciando Web App de Analisis Climatico
echo ==========================================
echo Carpeta: %CD%
echo(

set "VENV_NAME=env_climate_app"

python --version >nul 2>&1
if errorlevel 1 goto err_no_python

if not exist "requirements.txt" goto err_no_req
if not exist "app.py" goto err_no_app

where conda >nul 2>&1
if not errorlevel 1 goto use_conda
goto use_pip

:use_conda
echo [INFO] Conda detectado. Usando metodo robusto (recomendado).

set "CONDA_EXE=conda"
where mamba >nul 2>&1
if not errorlevel 1 set "CONDA_EXE=mamba"

echo [INFO] Usando: !CONDA_EXE!

if exist "%VENV_NAME%\conda-meta" goto conda_env_exists
if exist "%VENV_NAME%" (
    echo [WARNING] Carpeta '%VENV_NAME%' existe pero NO es un entorno Conda valido.
    echo [INFO] Eliminando carpeta conflictiva para reinstalar...
    rmdir /s /q "%VENV_NAME%"
    if exist "%VENV_NAME%" (
        echo [ERROR] No se pudo eliminar '%VENV_NAME%'. Por favor borrela manualmente.
        goto error_install
    )
)

echo [INFO] Creando entorno Conda local...
call !CONDA_EXE! create --prefix "./%VENV_NAME%" python=3.11 -y
if errorlevel 1 goto error_install

echo [INFO] Instalando librerias pesadas via Conda-Forge...
call !CONDA_EXE! install --prefix "./%VENV_NAME%" -c conda-forge geopandas rioxarray xarray netCDF4 matplotlib scipy numpy python-docx -y
if errorlevel 1 goto error_install

echo [INFO] Instalando librerias restantes via Pip...
call "%VENV_NAME%\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error_install

goto launch

:conda_env_exists
echo [INFO] Entorno Conda encontrado en ./%VENV_NAME%
echo [INFO] Verificando/Actualizando via Pip...
call "%VENV_NAME%\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto error_install
goto launch


:use_pip
echo [INFO] Conda NO detectado. Usando Python estandar (Pip).
echo [WARNING] Si esto falla con errores de "Build", por favor instale Miniforge.

if exist "%VENV_NAME%\Scripts\python.exe" goto venv_exists

echo [INFO] Configurando entorno virtual standard...
python -m venv "%VENV_NAME%"
if errorlevel 1 goto error_install

call "%VENV_NAME%\Scripts\activate.bat"

echo [INFO] Actualizando PIP (CRITICO para evitar errores de compilacion)...
python -m pip install --upgrade pip
if errorlevel 1 goto error_install

echo [INFO] Intentando instalar wheel de Numpy primero...
python -m pip install "numpy<2.0.0" --only-binary :all:
if errorlevel 1 goto error_install

echo [INFO] Instalando resto de librerias...
pip install -r requirements.txt
if errorlevel 1 goto error_install

goto launch

:venv_exists
echo [INFO] Entorno VENV encontrado.
call "%VENV_NAME%\Scripts\activate.bat"
pip install -r requirements.txt
if errorlevel 1 goto error_install
goto launch


:launch
echo(
echo [INFO] Lanzando aplicacion...
echo Si el navegador no se abre, vaya a: http://localhost:8501
echo Presione Ctrl+C para detener.
echo(

set "PROJ_LIB="
set "GDAL_DATA="

if exist "%VENV_NAME%\python.exe" (
  "%VENV_NAME%\python.exe" -m streamlit run app.py
) else (
  python -m streamlit run app.py
)

echo(
echo [INFO] Streamlit termino o se cerro.
pause
exit /b 0


:err_no_python
echo [ERROR] Python no encontrado. Instale Python 3.10+ y agreguelo al PATH.
pause
exit /b 1

:err_no_req
echo [ERROR] No encuentro requirements.txt en: %CD%
pause
exit /b 1

:err_no_app
echo [ERROR] No encuentro app.py en: %CD%
pause
exit /b 1

:error_install
echo(
echo [ERROR] Fallo la instalacion.
echo ---------------------------------------------------------
echo POSIBLE SOLUCION:
echo 1. Si usa Windows, instale MINIFORGE (ver manual).
echo 2. Asegurese de marcar "Add to PATH" al instalarlo.
echo 3. Intente de nuevo.
echo ---------------------------------------------------------
pause
exit /b 1
