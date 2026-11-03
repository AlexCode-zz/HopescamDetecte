# Decisiones de diseño — HopeScan

Registra las decisiones tomadas durante el refactor, el porqué de cada una y la
opción más conservadora elegida cuando había ambigüedad.

## D-001: Número de clases del modelo (FASE 0)

**Hecho:** se inspeccionó `modelo_cancer_mobilenet.pth` y la forma de
`classifier.1.weight` es `(3, 1280)`, es decir, el modelo fue entrenado con **3 clases**.

**Decisión:** mantener `CLASSES = ["Benigno", "Maligno", "Normal"]` en la app y registrar
que `inferencia_cancer2.py` estaba desalineado (usaba 2 clases). El CLI nuevo
`cli/predict.py` usa las 3 clases correctas.

## D-002: `torch.load` con `weights_only=True`

**Decisión:** cargar los pesos con `torch.load(..., weights_only=True)` para evitar
la ejecución de objetos pickle arbitrarios. Se verificó que el `state_dict` real
carga sin alterar pesos ni arquitectura. Si en el futuro un checkpoint no carga
con esta opción, se documenta el motivo antes de relajarla.

## D-003: Nombre del producto

**Decisión:** unificar en **HopeScan**. `APP_NAME = "HopeScan"` es la fuente de
verdad interna y la UI visible usa ese nombre. Se eliminaron las referencias a
«EcoScan» y «HopeScam» de los textos de la aplicación.

## D-004: Contraseña de búsqueda

**Decisión:** leer `SEARCH_PASSWORD` de la variable de entorno o de
`.streamlit/secrets.toml`. **No hay contraseña por defecto.** Si está vacía o no
existe, la pestaña de búsqueda queda deshabilitada con instrucciones para
configurarla. La comparación usa `hmac.compare_digest` y un `AttemptLimiter`
limita los intentos fallidos por sesión. La plantilla de secretos se versiona con
la contraseña vacía para no habilitar la búsqueda con un valor conocido.

Nota: Streamlit promueve los valores de `st.secrets` a `os.environ`. Por eso se
recomienda configurar la contraseña en un solo lugar (entorno o secrets, no ambos).

## D-005: Datos personales (`patient_records.csv`)

**Decisión:** sacar `patient_records.csv` del control de versiones (datos reales,
incluidos menores). La app usa `data/patient_records.csv`, ignorado por
`.gitignore`, y crea el CSV vacío si no existe. Se versiona
`data/sample_patient_records.csv` con filas ficticias.

El archivo real **sigue presente en el historial público** en el commit
`5cd0be5`. La purga requiere reescribir historial y fuerza un push; está
documentada en `docs/LIMPIEZA_HISTORIAL.md` y **no se ejecuta sin confirmación
explícita**.

## D-006: Requisitos

**Decisión:** separar las dependencias para evitar instalar CUDA innecesariamente:

- `requirements-base.txt`: Streamlit, pandas, numpy, Pillow.
- `requirements.txt`: base + torch/torchvision de PyPI (macOS u otros).
- `requirements-cpu.txt`: base + torch/torchvision `+cpu` desde el índice de PyTorch
  (Linux/CI).
- `requirements-rag.txt`: SDK opcional de Anthropic.
- `requirements-dev.txt`: pytest, pytest-cov, ruff.

Las versiones fijadas se probaron en Python 3.13.5. `opencv-python` no se incluye
porque no se usa.

## D-007: Tests de caracterización

Los tests de `tests/test_characterization.py` capturan el comportamiento de la
lógica pura (carga del modelo, predicción, persistencia CSV, validaciones y
respuestas del chatbot). Se mantienen como red de seguridad del refactor. Los
textos visibles de la UI pueden cambiar sin romper estos tests; el contrato de
seguridad OOD se prueba en `tests/test_ood.py` y el flujo completo en
`tests/test_smoke_apptest.py`.

## D-008: Género y DUI

El formulario ofrece «Femenino», «Masculino», «Otro» y «Prefiero no decir». El DUI
es obligatorio solo para mayores de 18 años; para menores se guarda
«Menor de 18» y no se solicita el documento. En la búsqueda, el DUI se muestra
enmascarado (`••••••67-8`) para reducir la exposición visual.

## D-009: Contrato de seguridad OOD

**Problema:** el modelo devolvía 99.7 % «Normal» sobre un gris plano y 100 % sobre
una imagen negra. La confianza softmax por sí sola no detecta imágenes fuera de
dominio.

**Decisión:** pipeline en dos capas:

1. **Heurísticas** (`src/hopescan/ood/`): resolución, proporción, color, nitidez,
   entropía, textura, rango de grises y moteado de ultrasonido.
2. **Energy score** (`T * logsumexp(logits/T)`) calculado con el modelo.

Estados finales:

- `no_es_ecografia_mamaria`: la imagen no pasa las heurísticas o el energy score
  es alto. **No se ejecuta el modelo** en el primer caso y nunca se muestra clase.
- `valida_no_concluyente`: la imagen parece una ecografía, pero la confianza
  calibrada o el margen entre clases son bajos. No se fuerza una clase.
- `valida_confiable`: solo aquí se muestran clase, probabilidades y Grad-CAM.

Los umbrales están en `models/ood_calibration.json` y son **provisionales**,
derivados de fixtures sintéticos. Las métricas clínicas (`auc_roc`,
`fpr_at_95tpr`, `ece`) quedan en `null` hasta tener un dataset real etiquetado.

## D-010: Grad-CAM

**Decisión:** generar un mapa Grad-CAM solo para resultados `valida_confiable`.
Se implementa con hooks de PyTorch y una rampa de color en numpy, sin añadir
matplotlib. El mapa indica dónde se fijó el modelo, no localiza una lesión ni
confirma un diagnóstico; la UI lo dice explícitamente.

## D-011: Chatbot con RAG

**Decisión:** sustituir el chat de reglas por recuperación local TF-IDF sobre
`rag/knowledge/`, con citas y guardrails. Orden de respuesta:

1. Guardrails (crisis, urgencia, diagnóstico, medicación, prompt injection).
2. Claude, si `ANTHROPIC_API_KEY` y `ANTHROPIC_MODEL` están configurados.
3. Respuesta extractiva con las frases más relevantes y fuentes citadas.
4. Saludos y fallback de reglas.

La recuperación ordena primero por cobertura de términos de la pregunta y luego
por similitud TF-IDF; así una sección que responde la pregunta gana a un
fragmento corto con una sola palabra repetida. Los documentos versionados son
**ejemplos** y deben sustituirse por fuentes oficiales antes de un uso real.

## D-012: Modo demostración

**Decisión:** incluir un modo que rellena datos ficticios, usa una ecografía
sintética versionada (`assets/demo/ecografia_sintetica.png`) y no guarda el
resultado en la base local. Sirve para probar la app sin manipular datos reales.
La imagen está etiquetada como sintética en la UI.

## D-013: Rediseño visual

**Decisión:** usar el tema nativo de `.streamlit/config.toml` (paleta rosa/magenta,
modo claro y oscuro, radios y tipografía) y componentes nativos de Streamlit
(`st.container`, `st.badge`, `st.metric`, `st.progress`, `st.chat_message`,
`st.write_stream`). Se eliminó el CSS del chat flotante y no se inyecta
JavaScript. Se evita `use_container_width` (deprecado) en favor de
`width="stretch"`/`width="content"`.
