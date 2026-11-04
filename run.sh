#!/usr/bin/env bash
################################################################################
# run.sh — HopeScan
#
# Script todo-en-uno para levantar la aplicación de un solo comando.
#
# Qué hace:
#   1. Detecta el sistema operativo (Linux/macOS o Git Bash en Windows).
#   2. Crea el entorno virtual (.venv) si no existe.
#   3. Activa el entorno virtual.
#   4. Instala las dependencias (variante CPU en Linux/Windows; PyPI en macOS).
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
    # virtualenv / uv no dependen de ensurepip (a diferencia de python3 -m venv)
    if command -v virtualenv >/dev/null 2>&1; then
        virtualenv "$VENV_DIR" >/dev/null 2>&1
    elif command -v uv >/dev/null 2>&1; then
        uv venv "$VENV_DIR" >/dev/null 2>&1
    else
        error "No se puede crear $VENV_DIR/: faltan virtualenv o uv."
        info "Instala python3-venv (apt install python3.13-venv) o virtualenv."
        exit 1
    fi
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
    VENV_PIP="$VENV_DIR/Scripts/pip"
else
    ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
    VENV_PIP="$VENV_DIR/bin/pip"
fi

if [ ! -f "$ACTIVATE_SCRIPT" ]; then
    error "No se encontró el script de activación: $ACTIVATE_SCRIPT"
    exit 1
fi

# shellcheck disable=SC1090
source "$ACTIVATE_SCRIPT"
ok "Entorno virtual activado."

# -----------------------------------------------------------------------------
# 5. Instalar dependencias Python (incluye el API FastAPI para el frontend React)
# -----------------------------------------------------------------------------
if [ -f "requirements.txt" ]; then
    REQ_FILE="requirements.txt"
    # La variante CPU solo está publicada para Linux/Windows en el índice de PyTorch.
    # En macOS se instala desde PyPI (los wheels ya son CPU).
    if [ "$SISTEMA" != "macos" ] && [ -f "requirements-cpu.txt" ]; then
        REQ_FILE="requirements-cpu.txt"
    fi

    info "Instalando dependencias de Python de $REQ_FILE (puede tardar unos minutos)..."
    "$VENV_PIP" install --upgrade pip >/dev/null 2>&1 || true
    if ! "$VENV_PIP" install -r "$REQ_FILE"; then
        if [ "$REQ_FILE" = "requirements-cpu.txt" ]; then
            warn "Falló la instalación CPU; reintentando con requirements.txt (PyPI)."
            "$VENV_PIP" install -r requirements.txt
        else
            error "No se pudieron instalar las dependencias de Python."
            exit 1
        fi
    fi
    ok "Dependencias de Python instaladas."
else
    warn "No se encontró requirements.txt; se omite la instalación de dependencias de Python."
fi

# Dependencias del API (FastAPI, uvicorn, python-multipart) para el frontend React.
# Se instalan en un entorno virtual separado (.venv-api/) porque FastAPI y
# Streamlit requieren versiones incompatibles de starlette y no pueden
# coexistir en el mismo entorno.
if [ -f "requirements-api.txt" ]; then
    API_VENV=".venv-api"
    if [ ! -d "$API_VENV" ]; then
        info "Creando entorno virtual separado para el API ($API_VENV/)..."
        # virtualenv no depende de ensurepip (a diferencia de python3 -m venv)
        if command -v virtualenv >/dev/null 2>&1; then
            virtualenv "$API_VENV" >/dev/null 2>&1
        elif command -v uv >/dev/null 2>&1; then
            uv venv "$API_VENV" >/dev/null 2>&1
        else
            error "No se puede crear $API_VENV/: faltan virtualenv o uv."
            info "Instala python3-venv (apt install python3.13-venv) o usa otro entorno."
            exit 1
        fi
        ok "Entorno del API creado."
    fi
    if [ "$SISTEMA" = "windows" ]; then
        API_PIP="$API_VENV/Scripts/pip"
        API_UVICORN="$API_VENV/Scripts/uvicorn"
    else
        API_PIP="$API_VENV/bin/pip"
        API_UVICORN="$API_VENV/bin/uvicorn"
    fi
    info "Instalando dependencias del API FastAPI (requirements-api.txt) en $API_VENV/..."
    "$API_PIP" install --upgrade pip >/dev/null 2>&1 || true
    if ! "$API_PIP" install -r requirements-api.txt >/dev/null 2>&1; then
        error "No se pudieron instalar las dependencias del API."
        exit 1
    fi
    ok "Dependencias del API instaladas en $API_VENV/."
fi

# Asegurar que .venv/ no tenga fastapi (conflicto de starlette con Streamlit)
if [ -d ".venv" ] && [ -f ".venv/bin/pip" ]; then
    if .venv/bin/pip show fastapi >/dev/null 2>&1; then
        warn "Desinstalando fastapi de .venv/ (incompatible con Streamlit/starlette)..."
        .venv/bin/pip uninstall -y fastapi uvicorn starlette python-multipart >/dev/null 2>&1 || true
        ok "fastapi removido de .venv/."
    fi
fi

# -----------------------------------------------------------------------------
# 6. Instalar y construir el frontend React (Vite + Tailwind)
# -----------------------------------------------------------------------------
if [ -f "frontend/package.json" ] && command -v npm >/dev/null 2>&1; then
    info "Instalando dependencias de Node (frontend/)..."
    ( cd frontend && npm install --no-audit --no-fund >/dev/null 2>&1 )
    ok "Dependencias de Node instaladas."

    info "Construyendo el frontend React (vite build)..."
    ( cd frontend && npm run build >/dev/null 2>&1 )
    ok "Frontend construido en frontend/dist/."
else
    warn "No se encontró frontend/package.json o npm no está disponible; se omite el frontend."
fi

# -----------------------------------------------------------------------------
# 6. Preparar archivos de configuración (sin sobrescribir existentes)
# -----------------------------------------------------------------------------
if [ -f ".env.example" ] && [ ! -f ".env" ]; then
    cp .env.example .env
    ok "Archivo .env creado a partir de .env.example."
    warn "Streamlit no carga .env automáticamente; usa .streamlit/secrets.toml o exporta las variables."
elif [ -f ".env" ]; then
    ok "Archivo .env ya existe (se conserva)."
    warn "Recuerda que Streamlit no carga .env automáticamente; usa secrets.toml o exporta las variables."
else
    warn "No hay .env.example; se omite la creación de .env."
fi

if [ -f ".streamlit/secrets.toml.example" ] && [ ! -f ".streamlit/secrets.toml" ]; then
    cp .streamlit/secrets.toml.example .streamlit/secrets.toml
    ok "Archivo .streamlit/secrets.toml creado a partir del ejemplo."
    warn "Edita .streamlit/secrets.toml y define SEARCH_PASSWORD para habilitar la búsqueda."
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
# 7. Lanzar la aplicación (API FastAPI + frontend React)
# -----------------------------------------------------------------------------
ok "Todo listo. Iniciando HopeScan..."
info "La app estará disponible en: http://localhost:5173 (frontend React)"
info "El API FastAPI correrá en: http://localhost:8000"
warn "Presiona Ctrl+C para detener la aplicación."
echo "------------------------------------------------------------"

# Iniciar el API FastAPI en segundo plano (desde el entorno separado .venv-api/)
if [ "$SISTEMA" = "windows" ]; then
    API_UVICORN=".venv-api/Scripts/uvicorn"
else
    API_UVICORN=".venv-api/bin/uvicorn"
fi
if [ -x "$API_UVICORN" ]; then
    "$API_UVICORN" api.main:app --host 127.0.0.1 --port 8000 > /tmp/opencode/hopescan-api.log 2>&1 &
else
    error "No se encontró uvicorn en $API_UVICORN. Ejecuta ./run.sh primero para instalar dependencias."
    exit 1
fi
API_PID=$!

# Iniciar el servidor de desarrollo de Vite (frontend React)
( cd frontend && npx vite --host --port 5173 > /tmp/opencode/hopescan-frontend.log 2>&1 ) &
FRONTEND_PID=$!

# Limpiar procesos al salir
cleanup() {
    kill "$API_PID" "$FRONTEND_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup EXIT

# Esperar a que terminen los procesos
wait
