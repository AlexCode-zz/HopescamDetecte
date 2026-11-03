"""Pestaña «Buscar paciente» con autenticación y DUI enmascarado.

Reglas de seguridad:

- Si no hay ``SEARCH_PASSWORD`` configurada, la búsqueda queda deshabilitada.
  No existe contraseña por defecto.
- La comparación usa ``hmac.compare_digest``.
- Se limita el número de intentos fallidos por sesión.
- El DUI se muestra enmascarado en la tabla; la búsqueda por DUI completo
  sigue funcionando porque el filtro se aplica sobre los datos originales.
"""

from __future__ import annotations

import streamlit as st

from ..auth import AttemptLimiter, verify_search_password
from ..config import get_search_password
from ..patients import load_patient_db, mask_dui, search_patients


def _get_limiter() -> AttemptLimiter:
    limiter = st.session_state.get("search_limiter")
    if not isinstance(limiter, AttemptLimiter):
        limiter = AttemptLimiter()
        st.session_state.search_limiter = limiter
    return limiter


def _logout() -> None:
    st.session_state.auth_search = False
    st.session_state.search_limiter = AttemptLimiter()
    st.session_state.pop("password_input", None)


def _render_disabled() -> None:
    st.warning(
        title="Búsqueda deshabilitada",
        body=(
            "No hay una contraseña de búsqueda configurada. Por seguridad, no "
            "existe una contraseña por defecto."
        ),
        icon=":material/lock:",
    )
    with st.expander("Cómo habilitar la búsqueda", expanded=False):
        st.markdown(
            "Define `SEARCH_PASSWORD` en `.streamlit/secrets.toml` o como "
            "variable de entorno. Puedes generar un valor seguro con:\n\n"
            "```bash\n"
            'python -c "import secrets; print(secrets.token_urlsafe(32))"\n'
            "```\n\n"
            "Después reinicia la aplicación. No commitees el archivo de secretos."
        )


def _render_login() -> None:
    limiter = _get_limiter()
    with st.container(border=True):
        st.markdown("#### Acceso restringido")
        st.caption(
            "La base contiene datos personales. Ingresa la contraseña para "
            "consultar los registros."
        )
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
                icon=":material/login:",
                key="btn_ingresar",
            )

            if ingresar:
                if limiter.is_blocked():
                    st.error(
                        "Demasiados intentos fallidos. Espera unos minutos antes "
                        "de volver a intentarlo.",
                        icon=":material/block:",
                    )
                elif verify_search_password(password_input):
                    limiter.reset()
                    st.session_state.auth_search = True
                    st.rerun()
                else:
                    limiter.register_failure()
                    remaining = limiter.remaining()
                    if remaining <= 0:
                        st.error(
                            "Contraseña incorrecta. Se alcanzó el límite de "
                            "intentos; espera unos minutos.",
                            icon=":material/error:",
                        )
                    else:
                        st.error(
                            f"Contraseña incorrecta. Intentos restantes: {remaining}.",
                            icon=":material/error:",
                        )


def _render_results() -> None:
    st.divider()
    header_left, header_right = st.columns([3, 1], vertical_alignment="center")
    with header_left:
        st.subheader("Base de datos de pacientes registrados")
    with header_right:
        st.button(
            "Cerrar sesión",
            icon=":material/logout:",
            width="stretch",
            key="btn_cerrar",
            on_click=_logout,
        )

    df_db = load_patient_db()
    if df_db.empty:
        st.info(
            "La base de datos de pacientes está vacía. Los análisis se guardan "
            "automáticamente al finalizar.",
            icon=":material/database:",
        )
        return

    st.metric("Registros en la base local", len(df_db))

    search_term = (
        st.text_input(
            "Buscar por nombre, apellido o DUI",
            key="search_term",
            placeholder="Ej: Pérez o 01234567-8",
            help=(
                "El DUI se muestra enmascarado en la tabla, pero puedes buscar "
                "con el número completo."
            ),
        )
        .strip()
        .lower()
    )

    if search_term:
        filtered_df = search_patients(df_db, search_term)
        st.markdown(f"**Resultados encontrados:** {len(filtered_df)}")
        if filtered_df.empty:
            st.warning(
                "No se encontraron pacientes que coincidan con el término de búsqueda.",
                icon=":material/search_off:",
            )
            return
        display_df = filtered_df.sort_values(
            by="Fecha_Registro", ascending=False
        ).copy()
    else:
        st.caption(
            "Mostrando los últimos 10 registros. Usa el campo de búsqueda para filtrar."
        )
        display_df = (
            df_db.sort_values(by="Fecha_Registro", ascending=False).head(10).copy()
        )

    if "DUI" in display_df.columns:
        display_df["DUI"] = display_df["DUI"].map(mask_dui)

    st.dataframe(
        display_df,
        width="stretch",
        height=320,
        hide_index=True,
    )
    st.caption(
        "El DUI se muestra enmascarado. No compartas esta pantalla ni exportes "
        "los datos sin autorización."
    )


def view_buscar_paciente() -> None:
    """Pinta la pestaña «Buscar paciente» (protegida con contraseña)."""
    st.title("Búsqueda de pacientes")
    st.caption("Acceso restringido a la base de datos de registros.")

    if get_search_password() is None:
        _render_disabled()
        return

    if not st.session_state.get("auth_search", False):
        _render_login()
        return

    st.badge(
        "Sesión autenticada",
        icon=":material/lock_open:",
        color="green",
    )
    _render_results()
