# HopeScan

Apoyo a la detección temprana de cáncer de mama por ultrasonido — El Salvador.

> **Aviso médico importante:** HopeScan es una herramienta educativa de apoyo.
> **NO es un dispositivo médico y NO sustituye el diagnóstico de un profesional
> de la salud.** La interpretación final debe realizarla un oncólogo, radiólogo
> o profesional calificado. El modelo no está certificado como dispositivo médico.

## Qué hace

- Registra los datos mínimos del paciente y exige confirmar la autorización para
  analizar la imagen.
- **Valida que la imagen parezca una ecografía mamaria** antes de pasarla por el
  modelo. Si no lo parece, no se muestra ninguna clase ni ningún porcentaje.
- Si el modelo no tiene certeza suficiente, devuelve **«no concluyente»** y
  tampoco fuerza una clase. Esto evita presentar como «normal» una imagen dudosa.
- Solo cuando el estado es **válido y confiable** muestra la clase, las
  probabilidades calibradas y un mapa **Grad-CAM**.
- Genera un reporte HTML con el estado del análisis, la confianza, las
  probabilidades, el Grad-CAM cuando corresponde y el aviso médico.
- Guarda los registros en un CSV local y ofrece una búsqueda protegida con
  contraseña. Si no hay contraseña configurada, la búsqueda queda deshabilitada.
- Incluye un **chat RAG** con documentos locales, citas y guardrails de seguridad.
  Si se configura Claude, redacta con el LLM; si no, responde en modo extractivo.
- Incluye **modo demostración** con una ecografía sintética versionada.

## Estructura del repositorio

```
.
├─ app.py                          # entrypoint Streamlit
├─ inferencia_cancer3.py           # shim del punto de entrada original
├─ cli/predict.py                  # CLI argparse
├─ src/hopescan/
│  ├─ config.py model.py inference.py gradcam.py patients.py report.py auth.py
│  ├─ ood/                         # heurísticas + energy score + decisión final
│  ├─ rag/                         # chunking, TF-IDF, guardrails y chat
│  └─ ui/                          # nuevo_analisis, buscar_paciente, sidebar_info, chat_widget
├─ models/ood_calibration.json     # umbrales OOD provisionales (sin métricas clínicas)
├─ modelo_cancer_mobilenet.pth     # pesos del modelo (no se modifican)
├─ rag/knowledge/                  # documentos de ejemplo para el RAG
├─ assets/demo/                    # ecografía sintética para demostración
├─ data/
│  ├─ patient_records.csv          # REAL — ignorado por git
│  └─ sample_patient_records.csv   # filas ficticias (versionado)
├─ tests/                          # unidad, OOD, RAG, reporte y smoke AppTest
├─ docs/                           # auditoría, decisiones, arquitectura, progreso y limpieza
├─ .github/workflows/ci.yml
└─ requirements*.txt  .env.example  .streamlit/secrets.toml.example  .gitignore
```

## Requisitos

- Python 3.10+ (probado con 3.13.5).
- Linux/CI: `pip install -r requirements-cpu.txt` (evita dependencias CUDA).
- macOS u otros: `pip install -r requirements.txt` (wheel de PyPI).
- Chat con Claude (opcional): `pip install -r requirements-rag.txt`.
- Desarrollo: `pip install -r requirements-dev.txt`.

## Instalación

```bash
# Opción rápida: crea el venv, instala dependencias, copia plantillas y lanza la app
./run.sh

# Opción manual
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows
pip install -r requirements-cpu.txt  # o requirements.txt en macOS
pip install -r requirements-dev.txt  # opcional: pytest, ruff
streamlit run app.py
```

La app estará disponible en `http://localhost:8501`. También se puede abrir el
shim legado con `streamlit run inferencia_cancer3.py`.

## Configuración de secretos

La contraseña de búsqueda se lee de `SEARCH_PASSWORD`, ya sea como variable de
entorno o desde `.streamlit/secrets.toml`. **No existe contraseña por defecto:**
si está vacía o no está definida, la pestaña de búsqueda muestra un aviso y no
permite autenticarse.

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# edita .streamlit/secrets.toml y define SEARCH_PASSWORD
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`run.sh` copia la plantilla con la contraseña vacía, de modo que la búsqueda
queda deshabilitada hasta que la configures. En despliegues sin archivo de
secretos, exporta `SEARCH_PASSWORD` en el entorno del proceso. El archivo
`.env.example` es solo una plantilla: Streamlit no carga `.env` automáticamente.

Chat con Claude (opcional):

```toml
# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-..."
ANTHROPIC_MODEL = "nombre-del-modelo-vigente"
```

Sin esas dos claves, el chat funciona con recuperación local y citas. Si las
configuras, la pregunta y los fragmentos recuperados se envían a la API de
Anthropic; las imágenes nunca se envían al chat.

**Nunca commitees** `.env`, `.streamlit/secrets.toml`, `.venv/` ni
`data/patient_records.csv`.

## Uso

### Nuevo análisis

1. Completa nombres, apellidos, edad, género y DUI (obligatorio solo para
   mayores de 18 años). Confirma que tienes autorización para analizar la imagen.
2. Sube una ecografía en escala de grises (PNG, JPG, WEBP, BMP o TIFF, máximo
   15 MB) o usa la imagen sintética de demostración.
3. Pulsa **«Analizar con IA»**. El resultado puede ser:
   - **Imagen no válida:** no se muestra clase ni porcentaje.
   - **No concluyente:** no se fuerza una clase; se explica el motivo.
   - **Válido y confiable:** se muestra la clase, la confianza calibrada, las
     probabilidades y el Grad-CAM.
4. Descarga el reporte HTML y llévalo a una consulta profesional. Para PDF,
   abre el HTML e imprime con «Guardar como PDF».

El **modo demostración** rellena datos ficticios, usa una imagen sintética y no
guarda el resultado en la base local.

### Buscar paciente

Introduce la contraseña configurada. La tabla muestra el DUI enmascarado; la
búsqueda por DUI completo sigue funcionando porque el filtro se aplica antes de
enmascarar. Hay un límite de intentos fallidos por sesión.

### Chat educativo

Pregunta por prevención, factores de riesgo, autoexamen, mamografía, ecografía,
síntomas o cómo interpretar un resultado. Cada respuesta incluye las fuentes
recuperadas y pasa por guardrails que rechazan diagnósticos, medicación,
urgencias, crisis e intentos de inyección de instrucciones.

Los documentos de `rag/knowledge/` son **ejemplos**. Deben sustituirse por
material oficial de la OMS, la American Cancer Society, el NCI o el MINSAL antes
de usar el chat en un contexto real.

### CLI

```bash
python -m cli.predict --image foto.png --model models/modelo_cancer_mobilenet.pth
```

## Tests y calidad

```bash
pytest                         # suite completa (107 tests)
pytest tests/ -q               # mismo comando que usa CI
pytest --cov=src/hopescan      # cobertura opcional
ruff check src/ app.py inferencia_cancer3.py cli/ tests/
ruff format --check src/ app.py inferencia_cancer3.py cli/ tests/
```

La suite cubre el contrato OOD (una imagen inválida nunca llega al modelo y
nunca produce una clase), Grad-CAM, el reporte HTML seguro, el RAG, los
guardrails, la autenticación y un flujo completo con `streamlit.testing.AppTest`.

## CI

`.github/workflows/ci.yml` instala `requirements-cpu.txt` y
`requirements-dev.txt`, ejecuta `ruff check`, `ruff format --check` y
`pytest tests/ -q` en cada push a `main` o
`refactor/estructura-y-estabilidad` y en PR a `main`.

## Privacidad de datos

- `data/patient_records.csv` contiene datos personales sensibles y está ignorado
  por Git. No se versiona.
- `data/sample_patient_records.csv` contiene filas ficticias para pruebas.
- Las imágenes se procesan en memoria y no se guardan en el CSV.
- El DUI se muestra enmascarado en la búsqueda.
- Si configuras Claude, solo la pregunta y los fragmentos de texto se envían a
  Anthropic. No se envían imágenes.
- El repositorio público tuvo un `patient_records.csv` real en el historial. Sigue
  las instrucciones de [`docs/LIMPIEZA_HISTORIAL.md`](docs/LIMPIEZA_HISTORIAL.md)
  para purgarlo; la reescritura de historial requiere confirmación explícita.

## Limitaciones del modelo y del OOD

- MobileNetV2 con 3 clases (Benigno / Maligno / Normal), entrenado externamente.
- No es un dispositivo médico certificado; los resultados son orientativos.
- La confianza no es una probabilidad de cáncer: mide la certeza técnica del
  modelo después de la calibración por temperatura.
- Los umbrales de `models/ood_calibration.json` son **provisionales** y se
  derivaron de fixtures sintéticos. No hay métricas clínicas: `auc_roc`,
  `fpr_at_95tpr` y `ece` están en `null` a propósito.
- El energy score y las heurísticas reducen falsos «normal», pero no sustituyen
  una validación con ecografías reales etiquetadas.
- Grad-CAM muestra dónde se fijó el modelo; no localiza una lesión ni confirma
  un diagnóstico.
- Una imagen válida pero ambigua produce «no concluyente»; eso no significa que
  exista una enfermedad.

## Roadmap

- [x] Refactor y separación lógica/UI
- [x] Validación OOD y estados seguros
- [x] Grad-CAM y reporte HTML sin clases forzadas
- [x] Chat RAG con citas y guardrails
- [x] Rediseño visual y modo demostración
- [x] Tests y CI
- [ ] Calibración OOD con un dataset real validado (BUSI u otro)
- [ ] Validación clínica externa del modelo
- [ ] Exportación nativa a PDF
- [ ] Autenticación de usuarios por roles
- [ ] Purga del historial de Git (pendiente de confirmación)
