# 🌍 Aplicación de Análisis Climático (Taller)

Esta carpeta contiene todo lo necesario para ejecutar el análisis de cambio climático en tu computador.

## 📂 ¿Qué contiene esta carpeta?

*   **`start_app.bat`**: 🖱️ **¡Dale doble clic aquí si usas Windows!** Instala y abre todo automáticamente.
*   **`start_app.command`**: 🍎 **¡Dale doble clic aquí si usas Mac!**
*   **`app.py`**: El código de la aplicación.
*   **`config/`, `scripts/`**: Archivos internos de configuración y cálculo.
*   **`inputs/`**: Carpeta donde se guardarán los datos climáticos y tus mapas.

## 🚀 ¿Cómo empezar?

1.  **Instalar Python (Miniforge Recomendado)**:
    *   Descarga el instalador de **Miniforge3** (Windows x86_64) desde: [https://github.com/conda-forge/miniforge](https://github.com/conda-forge/miniforge#miniforge3)
    *   ⚠️ **MUY IMPORTANTE**: Durante la instalación, marca las casillas:
        *   ✅ **"Add Miniforge3 to my PATH environment variable"**
        *   ✅ "Register Miniforge3 as my default Python 3.12"
2.  Si estás en **Windows**, ejecuta `start_app.bat`.
3.  Si estás en **Mac**, ejecuta `start_app.command`.
4.  Espera unos minutos la primera vez mientras se configuran las librerías.
5.  Se abrirá tu navegador con la aplicación.

## ⚠️ Nota Importante
No necesitas instalar nada manualmente (ni `pip`, ni librerías). El script se encarga de crear un entorno aislado (`env_climate_app`) para no interferir con tu sistema.
