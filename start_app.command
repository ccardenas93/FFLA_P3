#!/bin/bash
# Obtener el directorio donde está este script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================="
echo "   Iniciando Web App de Análisis Climático"
echo "=========================================="

# Nombre del entorno virtual
VENV_NAME="env_climate_app"

# Verificar si existe el entorno
if [ ! -d "$VENV_NAME" ]; then
    echo "⚙️  Configurando entorno por primera vez (esto tomará unos minutos)..."
    python3 -m venv "$VENV_NAME"
    
    # Activar
    source "$VENV_NAME/bin/activate"
    
    # Instalar dependencias
    echo "📦 Instalando librerías necesarias..."
    pip install --upgrade pip
    pip install -r requirements.txt
    
    if [ $? -ne 0 ]; then
        echo "❌ Error instalando dependencias. Verifique su conexión a internet."
        read -p "Presione Enter para salir..."
        exit 1
    fi
else
    echo "✅ Entorno encontrado. Verificando dependencias..."
    source "$VENV_NAME/bin/activate"
    # Always check dependencies to ensure updates are applied
    pip install -r requirements.txt
fi

# Ejecutar la app
echo "🚀 Lanzando aplicación..."
echo "Si el navegador no se abre, vaya a: http://localhost:8501"
echo "Presione Ctrl+C en esta ventana para detener la aplicación."

streamlit run app.py

# Desactivar al salir (opcional ya que se cierra la terminal)
deactivate
