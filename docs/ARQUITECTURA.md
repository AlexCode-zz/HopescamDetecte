# Arquitectura — HopeScan

Diagrama de flujo y estructura del sistema refactorizado (2026-11-03).

## Diagrama de flujo (Mermaid)

```mermaid
flowchart TD
    U((Usuario)) --> App[app.py — entrypoint Streamlit]

    App --> Sidebar[Sidebar: estado, aviso, guía, contactos]
    App --> Tabs[Pestañas: Nuevo análisis | Buscar paciente | Asistente educativo]

    subgraph Analisis[Flujo de análisis seguro]
        Tabs --> Form[Formulario + consentimiento]
        Form --> Demo{¿Modo demostración?}
        Demo -->|Sí| Synthetic[Ecografía sintética versionada]
        Demo -->|No| Upload[Subida de imagen]
        Synthetic --> Validate[Preparar imagen y heurísticas OOD]
        Upload --> Validate
        Validate -->|No parece ecografía| Reject[no_es_ecografia_mamaria: sin clase]
        Validate -->|Válida| Model[MobileNetV2: logits]
        Model --> Calib[Calibración por temperatura + energy score]
        Calib --> Decision{Decisión final}
        Decision -->|Confianza o margen bajos| NoConc[valida_no_concluyente: sin clase]
        Decision -->|Confiable| Confiable[valida_confiable: clase + probabilidades + Grad-CAM]
        Confiable --> Save[Guardar CSV local]
        Confiable --> Report[Reporte HTML seguro]
        NoConc --> Report
    end

    subgraph Busqueda[Flujo de búsqueda]
        Tabs --> Password{¿SEARCH_PASSWORD configurada?}
        Password -->|No| Disabled[Búsqueda deshabilitada]
        Password -->|Sí| Login[Login con compare_digest + límite de intentos]
        Login --> DB[(data/patient_records.csv)]
        DB --> Table[Tabla con DUI enmascarado]
    end

    subgraph RAG[Flujo del asistente]
        Tabs --> Guardrails[Guardrails: crisis, urgencia, diagnóstico, medicación, injection]
        Guardrails --> Retrieve[TF-IDF sobre rag/knowledge]
        Retrieve --> LLM{¿Claude configurado?}
        LLM -->|Sí| Claude[Claude + contexto + citas]
        LLM -->|No| Extractive[Respuesta extractiva + citas]
        Claude --> Sources[Fuentes citadas]
        Extractive --> Sources
    end

    subgraph Logica[Capa lógica src/hopescan]
        Config[config.py]
        OOD[ood/ — heurísticas + energy]
        Inference[inference.py — analyze_image]
        GradCAM[gradcam.py]
        Patients[patients.py — CSV, DUI, búsqueda]
        ReportMod[report.py — HTML escapado]
        Auth[auth.py — contraseña + limiter]
        RAGMod[rag/ — chunking, retriever, guardrails, chat]
    end

    App --> Config
    Validate --> OOD
    Model --> Inference
    Inference --> GradCAM
    Confiable --> Patients
    Report --> ReportMod
    Login --> Auth
    Retrieve --> RAGMod
```

## Estructura de directorios

```
.
├─ app.py                          # entrypoint Streamlit (layout + 3 pestañas)
├─ inferencia_cancer3.py           # shim: from app import main; main()
├─ src/hopescan/
│  ├─ config.py                    # constantes, rutas, estados OOD, secretos
│  ├─ model.py                     # MobileNetV2 + torch.load(weights_only=True)
│  ├─ inference.py                 # predict_logits, analyze_image, classify_ood
│  ├─ gradcam.py                   # Grad-CAM con hooks de PyTorch
│  ├─ patients.py                  # CSV atómico, validaciones, búsqueda, mask_dui
│  ├─ report.py                    # HTML escapado según estado OOD
│  ├─ auth.py                      # compare_digest + AttemptLimiter
│  ├─ chatbot.py                   # fallback de reglas (saludos)
│  ├─ ood/__init__.py              # heurísticas, energy score, decisión combinada
│  ├─ rag/
│  │  ├─ chunking.py               # Markdown → fragmentos
│  │  ├─ retriever.py              # TF-IDF + cobertura de términos
│  │  ├─ guardrails.py             # crisis, urgencia, diagnóstico, medicación, injection
│  │  └─ chat.py                   # guardrails → Claude opcional → extractivo
│  └─ ui/
│     ├─ nuevo_analisis.py         # formulario, consentimiento, demo, resultado
│     ├─ buscar_paciente.py        # login, búsqueda, DUI enmascarado
│     ├─ sidebar_info.py           # estado, aviso, guía, contactos
│     └─ chat_widget.py            # chat nativo con fuentes y sugerencias
├─ cli/predict.py                  # CLI argparse (--image, --model)
├─ models/ood_calibration.json     # umbrales provisionales + métricas null
├─ modelo_cancer_mobilenet.pth     # pesos (fallback a raíz)
├─ rag/knowledge/*.md              # documentos de ejemplo para el RAG
├─ assets/demo/ecografia_sintetica.png
├─ data/
│  ├─ patient_records.csv          # REAL (ignorado por .gitignore)
│  └─ sample_patient_records.csv   # filas ficticias (versionado)
├─ tests/
│  ├─ test_characterization.py     # caracterización de la lógica
│  ├─ test_hopescan.py             # unidad de src/hopescan
│  ├─ test_ood.py                  # contrato OOD + Grad-CAM + energy
│  ├─ test_rag.py                  # recuperación, guardrails, auth
│  ├─ test_report.py               # reporte HTML seguro
│  └─ test_smoke_apptest.py        # flujo UX con streamlit.testing.AppTest
├─ docs/ (AUDITORIA, DECISIONES, ARQUITECTURA, PROGRESO, LIMPIEZA_HISTORIAL)
├─ .github/workflows/ci.yml
└─ requirements*.txt, .env.example, .streamlit/secrets.toml.example, .gitignore
```

## Flujo de datos

1. **Entrada:** el formulario valida nombres/apellidos, edad 0–120 y DUI
   obligatorio solo para mayores de 18 (`########-#`). El consentimiento es
   obligatorio antes de analizar.
2. **Preparación:** PIL abre la imagen, corrige EXIF, convierte a RGB, valida
   tamaño/formato y calcula las heurísticas OOD. Una imagen inválida no llega al
   modelo.
3. **Inferencia:** MobileNetV2 con `Linear(1280, 3)` produce logits. Se aplica
   calibración por temperatura y softmax; se calcula el energy score.
4. **Decisión:** `combine_decision()` devuelve `valida_confiable`,
   `valida_no_concluyente` o `no_es_ecografia_mamaria`. La UI solo muestra clase,
   probabilidades y Grad-CAM en el primer estado.
5. **Persistencia:** registro atómico en `data/patient_records.csv` (temp +
   `os.replace`), DUI como string y sin guardar imágenes. En modo demostración no
   se escribe nada.
6. **Reporte:** HTML con escape de datos del paciente, estado, confianza,
   probabilidades, Grad-CAM opcional y aviso médico. Nunca inventa una clase.
7. **Búsqueda:** deshabilitada si no hay `SEARCH_PASSWORD`; si existe, usa
   `hmac.compare_digest` y un límite de intentos. El DUI se enmascara en la tabla.
8. **Chat:** guardrails primero; luego recuperación local TF-IDF y respuesta
   extractiva con citas. Si hay claves de Anthropic, Claude redacta usando solo
   el contexto recuperado. Sin claves no hay llamadas de red.

## Decisiones clave (ver `docs/DECISIONES.md`)

- Modelo entrenado con 3 clases (`classifier.1.weight` = `(3, 1280)`).
- `torch.load(..., weights_only=True)` verificado y mantenido.
- Nombre del producto unificado como `APP_NAME = "HopeScan"`.
- `patient_records.csv` real fuera del árbol actual, pero todavía en el historial
  (commit `5cd0be5`); purga pendiente de confirmación.
- OOD y calibración son provisionales: no hay métricas clínicas ni dataset real.
