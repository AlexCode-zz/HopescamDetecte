"""Contenido de la pestaña 'Buscar Paciente' con autenticación."""

from __future__ import annotations

import streamlit as st

from ..auth import verify_search_password
from ..patients import load_patient_db, search_patients
from ..config import get_search_password, is_dev_password_fallback


def view_buscar_paciente() -> None:
    """Pinta la pestaña 'Buscar Paciente' (protegida con contraseña).

    Hereda el comportamiento del código original: autenticación con password,
    búsqueda por nombre/apellido/DUI y tabla de últimos 10 registros por defecto.
    """
    st.subheader("🔒 Búsqueda de Pacientes - Acceso Restringido")
    st.write("Ingrese la contraseña para acceder a la base de datos de registros.")

    if not st.session_state.auth_search:
        password_input = st.text_input("Contraseña de Acceso", type="password")
        if st.button("🔑 Ingresar", type="primary"):
            if verify_search_password(password_input):
                st.session_state.auth_search = True
                st.success("Acceso concedido. Puede buscar pacientes ahora.")
            else:
                st.error("Contraseña incorrecta.")
        return

    # Sesión activa — mostrar warning si se está usando fallback dev (D-004)
    if is_dev_password_fallback(get_search_password()):
        st.warning("⚠️ Modo desarrollo: se está usando la contraseña por defecto SALUD123. Define SEARCH_PASSWORD en st.secrets o variable de entorno para producción.")

    st.markdown("---")
    st.subheader("🔍 Base de Datos de Pacientes Registrados")

    df_db = load_patient_db()
    if df_db.empty:
        st.warning("La base de datos de pacientes está vacía.")
        return

    search_term = st.text_input("Buscar por Nombre, Apellido o DUI:", key='search_term').strip().lower()

    if search_term:
        filtered_df = search_patients(df_db, search_term)
        st.markdown(f"**Resultados encontrados:** {len(filtered_df)}")
        if not filtered_df.empty:
            st.dataframe(filtered_df.sort_values(by='Fecha_Registro', ascending=False), use_container_width=True)
        else:
            st.warning("No se encontraron pacientes que coincidan con el término de búsqueda.")
    else:
        st.markdown("Mostrando los últimos 10 registros. Use el campo de búsqueda para filtrar.")
        st.dataframe(df_db.sort_values(by='Fecha_Registro', ascending=False).head(10), use_container_width=True)

    st.markdown("---")
    if st.button("🚪 Cerrar Sesión de Búsqueda"):
        st.session_state.auth_search = False
        st.rerun()
