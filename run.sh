#!/usr/bin/env bash
################################################################################
# run.sh — HopeScan / HopeScam
#
# Script todo-en-uno para levantar la aplicación de un solo comando.
#
# Qué hace:
#   1. Detecta el sistema operativo (Linux/macOS o Git Bash en Windows).
#   2. Crea el entorno virtual (.venv) si no existe.
#   3. Activa el entorno virtual.
#   4. Instala las dependencias de requirements.txt.
#   5. Copia los archivos de configuración de ejemplo (.env y secrets.toml)
#      si aún no existen (sin sobrescribir los tuyos).
#   6. Lanza la app con: streamlit run app.py
#
# Uso:
#   chmod +x run.sh
#   ./run.sh
#
# La app quedará disponible en http://localhost:8501
################################################################################
set -euo pipefail

# Directorio donde está este script (robusto sin importar desde dónde se llame)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colores para mensajes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # Sin color

info()  { printf "%b[INFO]%b  %s\n" "$BLUE" "$NC" "$*"; }
ok()    { printf "%b[OK]%b    %s\n" "$GREEN" "$NC" "$*"; }
warn()  { printf "%b[WARN]%b  %s\n" "$YELLOW" "$NC" "$*"; }
error() { printf "%b[ERROR]%b %s\n" "$RED" "$NC" "$*" >&2; }

# -----------------------------------------------------------------------------
# 1. Detectar SO y elegir comando de activación del venv
# -----------------------------------------------------------------------------
detectar_sistema() {
    case "$(uname -s)" in
        Linux*)     echo "linux" ;;
        Darwin*)    echo "macos" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)          echo "desconocido" ;;
    esac
}

SISTEMA="$(detectar_sistema)"
info "Sistema detectado: $SISTEMA"

# -----------------------------------------------------------------------------
# 2. Verificar Python
# -----------------------------------------------------------------------------
if ! command -v python3 >/dev/null 2>&1; then
    error "No se encontró python3. Instala Python 3.10+ y vuelve a intentar."
    exit 1
fi

PY_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
info "Python encontrado: $PY_VERSION"

# -----------------------------------------------------------------------------
# 3. Crear entorno virtual si no existe
# -----------------------------------------------------------------------------
VENV_DIR=".venv"

if [ ! -d "$VENV_DIR" ]; then
    info "Creando entorno virtual en $VENV_DIR/ ..."
    python3 -m venv "$VENV_DIR"
    ok "Entorno virtual creado."
else
    ok "Entorno virtual ya existe ($VENV_DIR/)."
fi

# -----------------------------------------------------------------------------
# 4. Activar entorno virtual
# -----------------------------------------------------------------------------
if [ "$SISTEMA" = "windows" ]; then
    # Git Bash / MSYS / Cygwin
    ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
else
    ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
fi

if [ ! -f "$ACTIVATE_SCRIPT" ]; then
    error "No se encontró el script de activación: $ACTIVATE_SCRIPT"
    exit 1
fi

# shellcheck disable=SC1090
source "$ACTIVATE_SCRIPT"
ok "Entorno virtual activado."

# -----------------------------------------------------------------------------
# 5. Instalar dependencias
# -----------------------------------------------------------------------------
if [ -f "requirements.txt" ]; then
    info "Instalando dependencias de requirements.txt (puede tardar unos minutos)..."
    python3 -m pip install --upgrade pip >/dev/null 2>&1 || true
    python3 -m pip install -r requirements.txt
    ok "Dependencias instaladas."
else
    warn "No se encontró requirements.txt; se omite la instalación de dependencias."
fi

# -----------------------------------------------------------------------------
# 6. Preparar archivos de configuración (sin sobrescribir existentes)
# -----------------------------------------------------------------------------
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    cp .env.example .env
    ok "Archivo .env creado a partir de .env.example."
elif [ -f ".env" ]; then
    ok "Archivo .env ya existe (se conserva)."
else
    warn "No hay .env.example; se omite la creación de .env."
fi

if [ -f ".streamlit/secrets.toml.example" ] && [ ! -f ".streamlit/secrets.toml" ]; then
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml
    ok "Archivo .streamlit/secrets.toml creado a partir del ejemplo."
elif [ -f ".streamlit/secrets.toml" ]; then
    ok "Archivo .streamlit/secrets.toml ya existe (se conserva)."
else
    warn "No hay .streamlit/secrets.toml.example; se omite su creación."
fi

# Asegurar que exista el directorio de datos
if [ ! -d "data" ]; then
    mkdir -p data
    ok "Directorio data/ creado."
fi

# -----------------------------------------------------------------------------
# 7. Lanzar la aplicación Streamlit
# -----------------------------------------------------------------------------
ok "Todo listo. Iniciando HopeScan..."
info "La app estará disponible en: http://localhost:8501"
warn "Presiona Ctrl+C para detener la aplicación."
echo "------------------------------------------------------------"

streamlit run app.py
