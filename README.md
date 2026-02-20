---
title: FFLA Climate Analysis
emoji: 🌍
colorFrom: green
colorTo: blue
sdk: streamlit
sdk_version: "1.32.0"
app_file: app.py
pinned: false
---
# Aplicación de Análisis Climático - FFLA

Este repositorio contiene las herramientas necesarias para la ejecución del taller de análisis de cambio climático. Asegúrese de seguir las instrucciones detalladas a continuación para garantizar el correcto funcionamiento de la aplicación en su equipo.

## Estructura del Repositorio

*   **`start_app.bat`**: Script de inicialización automatizada para sistemas **Windows**.
*   **`start_app.command`**: Script de inicialización automatizada para sistemas **macOS**.
*   **`app.py`**: Código fuente principal de la aplicación.
*   **`config/`, `scripts/`**: Módulos de configuración y lógica de procesamiento.
*   **`inputs/`**: Directorio destinado al almacenamiento de datos climáticos y cartografía base.

## Instrucciones de Inicio

### 1. Prerrequisitos del Sistema

Es necesario contar con un intérprete de Python instalado y correctamente configurado en las variables de entorno del sistema.

**Para usuarios de Windows:**
Se recomienda encarecidamente la instalación de **Miniforge** para gestionar las dependencias geospaciales de manera robusta.

1.  Descargue el instalador **Miniforge3-Windows-x86_64.exe** desde el repositorio oficial: [https://github.com/conda-forge/miniforge](https://github.com/conda-forge/miniforge#miniforge3)
2.  **IMPORTANTE**: Durante el proceso de instalación, es obligatorio **marcar** las siguientes casillas para asegurar que el sistema reconozca los comandos:
    *   [x] *Add Miniforge3 to my PATH environment variable* (Es posible que el instalador muestre una advertencia en rojo; ignórela y proceda a marcar la casilla).
    *   [x] *Register Miniforge3 as my default Python 3.12*

### 2. Ejecución de la Aplicación

Una vez configurados los prerrequisitos:

1.  **En Windows**: Ejecute el archivo `start_app.bat` haciendo doble clic sobre él.
2.  **En macOS**: Ejecute el archivo `start_app.command`.

El sistema iniciará un proceso automático para configurar un entorno virtual aislado (`env_climate_app`) e instalar las librerías necesarias. Este proceso puede tomar varios minutos la primera vez. Una vez finalizado, la aplicación se desplegará automáticamente en su navegador web predeterminado.

## Nota Técnica
No se requiere la instalación manual de librerías mediante `pip`. Los scripts proporcionados gestionan la creación del entorno de ejecución de forma autónoma para evitar conflictos con otras configuraciones del sistema.
