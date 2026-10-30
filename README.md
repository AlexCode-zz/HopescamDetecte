# HopeScam / HopeScan

Asistente de apoyo a la detección de cáncer de mama por ultrasonido — El Salvador.

> **⚠️ Aviso médico importante:** Esta aplicación es una herramienta de apoyo informativo y educativo.
> **NO SUSTITUYE, bajo ninguna circunstancia, el diagnóstico o la consulta con un profesional médico
> especialista (oncólogo o radiólogo).** La interpretación final debe ser realizada por un profesional
> de la salud calificado. El modelo de IA no está certificado como dispositivo médico.

## Descripción

HopeScan permite registrar los datos de un paciente, subir una imagen de ultrasonido de mama, obtener una
predicción de IA (clases: **Benigno / Maligno / Normal**) con nivel de confianza, guardar el registro en una
base de datos CSV y descargar un reporte en HTML (con la imagen incrustada en base64). Incluye una pestaña de
búsqueda de pacientes protegida con contraseña y un asistente de chat para dudas sobre prevención y síntomas.

El proyecto está en **refactor activo** sobre el código original (`inferencia_cancer3.py`). Se ha separado la
lógica pura (`src/hopescan/`) de la interfaz Streamlit (`app.py`), se ha unificado el chatbot (3 implementaciones
duplicadas → 1), se ha creado un CLI (`cli/predict.py`) y se han añadido tests y CI.

## Estructura del repositorio

```
.
├─ app.py                         # entrypoint Streamlit
├─ inferencia_cancer3.py          # shim del punto de entrada original
├─ src/hopescan/                  # lógica pura (sin Streamlit)
│  ├─ config.py  model.py  inference.py  patients.py  report.py  auth.py  chatbot.py
│  └─ ui/ (styles, nuevo_analisis, buscar_paciente, sidebar_info, chat_widget)
├─ cli/predict.py                 # CLI argparse (--image, --model)
├─ models/modelo_cancer_mobilenet.pth   # pesos del modelo (no se modifica)
├─ data/
│  ├─ patient_records.csv         # REAL — ignorado por git (datos sensibles)
│  └─ sample_patient_records.csv  # 5 filas ficticias (versionado)
├─ tests/                         # pytest (caracterización + unidad + smoke AppTest)
├─ docs/ (AUDITORIA.md, DECISIONES.md, ARQUITECTURA.md)
├─ .github/workflows/ci.yml
├─ requirements.txt  requirements-dev.txt  .env.example  .streamlit/secrets.toml.example  .gitignore
```

## Requisitos

- Python 3.10+ (probado con 3.13.5)
- `pip install -r requirements.txt` (instala torch en variante CPU)

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows

# 2. Instalar dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt   # opcional: pytest, ruff, pytest-cov

# 3. Ejecutar la app
streamlit run app.py
# o el comando legado:
streamlit run inferencia_cancer3.py
```

La app estará disponible en `http://localhost:8501`.

## Configuración de secretos

La contraseña de búsqueda se lee, por este orden:
1. `st.secrets["SEARCH_PASSWORD"]` (archivo `.streamlit/secrets.toml`)
2. Variable de entorno `SEARCH_PASSWORD`
3. Fallback de desarrollo `"SALUD123"` (se muestra un aviso `st.warning` visible solo en este caso)

Crea los archivos de ejemplo y ajusta los valores:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
cp .env.example .env
# edita .streamlit/secrets.toml con tu contraseña real
```

**Nunca commitees** `.env`, `.streamlit/secrets.toml`, `.venv/` ni `data/patient_records.csv`.

## Uso

### App Streamlit
1. Abre `streamlit run app.py`.
2. Pestaña **"Nuevo Análisis"**: llena el formulario (nombres, apellidos, edad, género, DUI si es mayor de 18).
3. Sube una imagen de ultrasonido (`.png`, `.jpg`, `.jpeg`).
4. Pulsa **"Iniciar Análisis Predictivo"**. Se muestra la clase, la confianza y el gráfico de probabilidades.
5. Descarga el reporte en HTML (incluye imagen y aviso médico).
6. Pestaña **"Buscar Paciente"**: autentícate con la contraseña y consulta registros.

### CLI
```bash
python -m cli.predict --image foto.png --model models/modelo_cancer_mobilenet.pth
```

## Tests

```bash
pytest                      # todos los tests (38)
pytest --cov=src/hopescan   # con cobertura
```

Cobertura mínima requerida ≥80 % en `inference`, `patients`, `chatbot`, `auth`, `report`.

Calidad:
```bash
ruff check src/ app.py inferencia_cancer3.py cli/ tests/
ruff format --check src/ app.py inferencia_cancer3.py cli/ tests/
```

## CI

Ver `.github/workflows/ci.yml`: instala dependencias (torch CPU), ejecuta `ruff` y `pytest` en cada push y PR.

## Privacidad de datos

- `patient_records.csv` contiene datos personales sensibles (incluidos menores) y **está ignorado por `.gitignore`**; no se versiona.
- Se creó `data/sample_patient_records.csv` con 5 filas ficticias para pruebas.
- Si `patient_records.csv` ya estuvo en algún commit del historial original, no se reescribe el historial (ver reporte final).

## Limitaciones del modelo

- El modelo es MobileNetV2 con 3 clases (Benigno / Maligno / Normal), entrenado externamente.
- No es un dispositivo médico certificado; los resultados son orientativos.
- Confianzas bajas (< 60 %) se advierten sin alterar el resultado mostrado.
- La confianza no es un porcentaje de cáncer; mide la certeza técnica del análisis.

## Roadmap

- [x] Refactor y separación lógica/UI
- [x] Chatbot unificado
- [x] Tests y CI
- [ ] Validación clínica externa del modelo
- [ ] Exportación a PDF nativa
- [ ] Autenticación de usuarios por roles
