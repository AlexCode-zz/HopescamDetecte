"""Gestión pura de la base de datos de pacientes CSV (sin Streamlit).

Incluye: carga, guardado atómico, validaciones de formulario y búsqueda.
"""

from __future__ import annotations

import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import PATIENT_DB_COLUMNS, resolve_patient_db_path

# Regex robusto para DUI salvadoriano: ### #### #### -> ###-####
DUI_PATTERN = re.compile(r"^\d{3}-\d{7}$")


def default_patient_data() -> dict:
    """Valores defaults de los campos del formulario (para test de validación)."""
    return {
        "nombres": "",
        "apellidos": "",
        "edad": 30,
        "genero": "Femenino",
        "dui": "",
    }


def validate_patient_form(*, nombres: str, apellidos: str, edad: int, dui: str) -> str | None:
    """Reglas de validación idénticas al formulario de la app original.

    Returns ``None`` cuando es válido; retorna una cadena de mensaje de error
    cuando hay problema (comportamiento conservador: no lanza ValueError en la
    app — se usará directamente con ``st.error``).
    """
    if not nombres or not apellidos:
        return "Por favor, complete los campos de Nombres y Apellidos."
    if edad < 0 or edad > 120:
        return "Edad debe estar entre 0 y 120."
    if edad >= 18 and not dui:
        return "Para pacientes mayores de 18 años, el DUI es obligatorio."
    return None


def get_current_dui(age: int) -> str:
    """Regla DUI para menores (<18) y adultos (vacío en normal flujo).

    Copia fiel del flujo ``dui = dui if edad >= 18 else 'Menor de 18'`` del formulario.
    """
    return "" if age >= 18 else "Menor de 18"


def build_record(patient_data: dict, scan_results: dict) -> dict:
    """Construye el diccionario de un nuevo registro a partir de inputs del usuario."""
    dui = patient_data["dui"] if patient_data["edad"] >= 18 else "Menor de 18"
    record = {
        "Nombres": patient_data["nombres"],
        "Apellidos": patient_data["apellidos"],
        "Edad": patient_data["edad"],
        "Género": patient_data["genero"],
        "DUI": dui,
        "Fecha_Registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Resultado_IA": scan_results.get("result", "N/A"),
        "Confianza_IA": scan_results.get("confidence", "N/A"),
    }
    return record


def save_patient_data(patient_data: dict, scan_results: dict) -> dict:
    """Guarda un nuevo paciente (escritura atómica) y retorna el registro escrito.

    Debe llamarse ANTES de ``st.session_state.current_dui`` de forma similar al
    comportamiento original, pero en lógica pura no hay sesión de Streamlit.
    """
    record = build_record(patient_data, scan_results)
    record["DUI"] = str(record["DUI"])
    for k in ("Nombres", "Apellidos"):
        record[k] = (record[k] or "").strip()

    df = load_patient_db()
    new_df = pd.DataFrame([record])
    df = pd.concat([df, new_df], ignore_index=True)
    atomic_write_csv(resolve_patient_db_path(), df)
    return record


def atomic_write_csv(path: Path, df: pd.DataFrame) -> None:
    """Escritura atómica: escribe a archivo temporal y ``os.replace`` al destino.

    Previene corrupciones concurrentes (FASE 3).
    """
    assert path.parent.exists(), f"Ruta padre no existe: {path.parent}"
    fd, tmp_name = tempfile.mkstemp(
        prefix=".tmp-hopescan-", suffix=".csv", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            df.to_csv(fh, index=False)
        os.replace(tmp_name, path)
    finally:
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass


def load_patient_db() -> pd.DataFrame:
    """Carga la base de datos de pacientes.

    Si el CSV no existe se crea uno vacío con el esquema completo (comportamiento
    conservado del original); si está corrupto, retorna un DataFrame vacío con
    las columnas esperadas.
    """
    try:
        path = resolve_patient_db_path()
        if path.exists():
            df = pd.read_csv(path, dtype={"DUI": str})
            missing = [c for c in PATIENT_DB_COLUMNS if c not in df.columns]
            if missing:
                df = pd.concat(
                    [pd.DataFrame(columns=PATIENT_DB_COLUMNS), df], ignore_index=True
                )
            else:
                return df
    except Exception:
        pass
    # No existe ni está corrupto: DataFrame vacío con esquema completo
    return pd.DataFrame(columns=PATIENT_DB_COLUMNS)


def search_patients(df: pd.DataFrame, term: str) -> pd.DataFrame:
    """Busca pacientes por nombre, apellido o DUI (búsqueda client-side).

    Retorna ``df`` solo si hay coincidencias; si el término está vacío retorna
    los últimos 10 registros por defecto.
    """
    if df is None or df.empty or not term or term.strip() == "":
        return df.head(10) if df.size else df
    t = term.strip().lower()
    mask = (
        df["Nombres"].astype(str).str.lower().str.contains(t, na=False)
        | df["Apellidos"].astype(str).str.lower().str.contains(t, na=False)
        | df["DUI"].astype(str).str.lower().str.contains(t, na=False)
    )
    filtered = df[mask].sort_values(by="Fecha_Registro", ascending=False)
    return filtered if filtered.size else pd.DataFrame()


def check_dui(dui: str) -> bool:
    """Valida DUI format (###-####); nunca bloqueará registros con 'Menor de 18'."""
    if not dui:
        return False
    stripped = str(dui).strip()
    if stripped == "Menor de 18":
        return True  # není válido internamente, pero el flujo de la app lo bloquea
    return bool(DUI_PATTERN.match(stripped))
