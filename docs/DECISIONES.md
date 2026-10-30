# Decisiones de diseño — HopeScan

Esta registra las decisiones tomadas durante el refactor, el porqué de cada una y la
opción más conservadora elegida cuando había ambigüedad (ver REGLA DE ORO del proyecto).

## D-001: Número de clases del modelo (FASE 0)

**Hecho:** se inspeccionó `modelo_cancer_mobilenet.pth` y la forma de
`classifier.1.weight` es `(3, 1280)`, es decir, el modelo fue entrenado con **3 clases**.

**Decisión:** mantener `CLASSES = ["Benigno", "Maligno", "Normal"]` en la app y registrar
que `inferencia_cancer2.py` estaba desalineado (usaba 2 clases: `["Benigno", "Maligno"]`).
No se cambia el comportamiento de la app (3 clases). El CLI nuevo `cli/predict.py` usará
las 3 clases correctas.

## D-002: torch.load con `weights_only=True`

**Decisión pendente de verificación:** usar `torch.load(..., weights_only=True)` para evitar
carga arbitraria de objetos pickle (mejora de seguridad sin cambiar pesos ni arquitectura).
Se verificará que el state_dict del .pth siga cargando con `weights_only=True`; si falla, se
documenta el motivo y se conserva `torch.load(path, map_location=device)`.

## D-003: Nombre del producto

**Decisión:** unificar en **"HopeScan"**. Se define `APP_NAME = "HopeScan"` en
`src/hopescan/config.py` y se usa como nombre interno, en el reporte HTML y en el footer.

**Conservadurismo:** el título visible de la app (`st.set_page_config` y el encabezado de la
columna derecha) se conserva tal cual para no alterar textos visibles ni el flujo UX
(restricción 1). El nombre de marca visible no se sustituye ciegamente; `APP_NAME` es la
única fuente de verdad interna y se deja constancia aquí para futuros cambios visibles.

## D-004: Contraseña de búsqueda

**Decisión:** leer de `st.secrets["SEARCH_PASSWORD"]` o variable de entorno `SEARCH_PASSWORD`;
si no está definida, usar `"SALUD123"` como fallback de desarrollo con un `st.warning`
visible solo en ese caso. Comparar con `hmac.compare_digest`. Se crean
`.env.example` y `.streamlit/secrets.toml.example`. No se commitea `.env` ni `secrets.toml`.

## D-005: Datos personales (patient_records.csv)

**Decisión:** sacar `patient_records.csv` del control de versiones (datos reales, incluidos
menores). Moverlo a `data/patient_records.csv` (ignorado por `.gitignore`). Crear
`data/sample_patient_records.csv` con 5 filas FICTICIAS (versionado). La app crea el CSV
real vacío si no existe (comportamiento conservado). El commit inicial de `main`
**ya incluye** `patient_records.csv` con datos reales: no se reescribe historial; se anota
como riesgo pendiente en el reporte final.

## D-006: Requisitos

**Decisión:** `requemens.txt` (typo y contenido roto) se reemplaza por
`requirements.txt` con versiones fijadas y probadas en este entorno (Python 3.13.5,
torch CPU). `opencv-python` **no** se incluye: no se usa en el código. Se añade
`requirements-dev.txt` (pytest, ruff).

## D-007: Tests de caracterización

Los tests de `tests/test_characterization.py` se escriben contra el código original con un
stub de `streamlit` (`tests/conftest.py`) porque el módulo original depende de Streamlit a
nivel de módulo. Pasan en el código original y seguirán pasando contra `src/hopescan`
después del refactor (mismas funciones y nombres).

## D-008: Género

El selector del formulario ofrece solo "Femenino" (comportamiento actual). Los registros
históricos con "Masculino" se conservan y la búsqueda/lectura los siguen soportando. No se
amplía el selector para no alterar el flujo UX.
