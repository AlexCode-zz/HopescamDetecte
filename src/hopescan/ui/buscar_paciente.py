"""Pestaña 'Buscar Paciente' con autenticación."""

from __future__ import annotations

import streamlit as st

from ..auth import verify_search_password
from ..config import get_search_password, is_dev_password_fallback
from ..patients import load_patient_db, search_patients


def view_buscar_paciente() -> None:
    """Pinta la pestaña 'Buscar Paciente' (protegida con contraseña)."""
    st.title("Búsqueda de pacientes")
    st.caption("Acceso restringido a la base de datos de registros.")

    if not st.session_state.get("auth_search", False):
        with st.form(key="search_login_form", border=False):
            password_input = st.text_input(
                "Contraseña de acceso",
                type="password",
                key="password_input",
                placeholder="Ingresa la contraseña",
            )
            ingresar = st.form_submit_button(
                "Ingresar",
                type="primary",
                width="stretch",
                key="btn_ingresar",
            )

            if ingresar:
                if verify_search_password(password_input):
                    st.session_state.auth_search = True
                    st.success("Acceso concedido.")
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
        return

    # Advertencia si se usa contraseña por defecto de desarrollo
    if is_dev_password_fallback(get_search_password()):
        st.warning(
            title="Modo desarrollo",
            body=(
                "Se está usando la contraseña por defecto (SALUD123). "
                "Define SEARCH_PASSWORD en st.secrets o variable de entorno para producción."
            ),
            icon=":material/info:",
        )

    st.divider()
    st.subheader("Base de datos de pacientes registrados")

    df_db = load_patient_db()
    if df_db.empty:
        st.info("La base de datos de pacientes está vacía.")
        return

    search_term = (
        st.text_input(
            "Buscar por nombre, apellido o DUI",
            key="search_term",
            placeholder="Ej: Pérez o 01234567-8",
        )
        .strip()
        .lower()
    )

    if search_term:
        filtered_df = search_patients(df_db, search_term)
        st.markdown(f"**Resultados encontrados:** {len(filtered_df)}")
        if not filtered_df.empty:
            st.dataframe(
                filtered_df.sort_values(by="Fecha_Registro", ascending=False),
                width="stretch",
                height=300,
            )
        else:
            st.warning(
                "No se encontraron pacientes que coincidan con el término de búsqueda."
            )
    else:
        st.caption(
            "Mostrando los últimos 10 registros. Usa el campo de búsqueda para filtrar."
        )
        st.dataframe(
            df_db.sort_values(by="Fecha_Registro", ascending=False).head(10),
            width="stretch",
            height=300,
        )

    st.divider()
    if st.button("Cerrar sesión de búsqueda", width="stretch", key="btn_cerrar"):
        st.session_state.auth_search = False
        st.rerun()
