# Arquitectura — HopeScan

Diagrama de flujo y estructura del sistema refactorizado.

## Diagrama de flujo (Mermaid)

```mermaid
flowchart TD
    Usuario((Usuario)) -->|streamlit run app.py| App[app.py - Entry Point Streamlit]
    
    App --> Sidebar[Columna Izquierda: Acerca / Contactos Médicos / Guía]
    App --> Tabs[Pestañas: Nuevo Análisis | Buscar Paciente]
    
    Tabs --> NA[Nuevo Análisis]
    Tabs --> BP[Buscar Paciente]

    subgraph Flujo Nuevo Análisis
        NA --> Form[Formulario: Nombres, Apellidos, Edad, Género, DUI]
        Form --> Valid{Validación}
        Valid -->|Inválido| Err[st.error - mensaje]
        Valid -->|Válido| Upload[Subida Imagen .png/.jpg/.jpeg]
        Upload --> Analizar[Botón Iniciar Análisis Predictivo]
        Analizar --> Modelo[(Modelo MobileNetV2 + pesos .pth)]
        Modelo --> Pred[predicción: clase + probabilidades]
        Pred --> Guardar[Guardar CSV paciente_records.csv]
        Guardar --> Resultados[Mostrar resultados + métrica + gráfico]
        Resultados --> Descarga[Descargar Reporte HTML]
    end

    subgraph Flujo Búsqueda
        BP --> Login[Contraseña de Acceso]
        Login -->|Correcta| DB[Cargar CSV pacientes]
        Login -->|Incorrecta| Err2[Contraseña incorrecta]
        DB --> Buscar[Campo búsqueda nombre/apellido/DUI]
        Buscar --> Tabla[Tabla últimos 10 / filtrados]
    end

    subgraph Chatbot
        Usuario --> Burbuja[Burbuja flotante 💬]
        Burbuja --> Caja[Caja de chat única]
        Caja --> Motor[motor responder() - reglas únicas]
    end

    subgraph Capa Lógica src/hopescan
        Config[config.py - constantes, rutas, secrets]
        Model[model.py - carga del modelo]
        Infer[inference.py - preprocesamiento + predicción]
        Patients[patients.py - CSV, validaciones, búsqueda]
        Report[report.py - HTML reporte]
        Auth[auth.py - hmac.compare_digest]
        Chat[chatbot.py - motor único de respuestas]
    end

    App --> Config
    App --> Model
    App --> Infer
    NA --> Patients
    NA --> Report
    BP --> Patients
    BP --> Auth
    Burbuja --> Chat

    style Usuario fill:#f9f,stroke:#333
    style Modelo fill:#bbf,stroke:#333
    style DB fill:#bfb,stroke:#333
```

## Estructura de directorios

```
.
├─ app.py                         # entrypoint Streamlit (orquesta layout + tabs)
├─ inferencia_cancer3.py          # shim: from app import main; main()
├─ src/hopescan/
│  ├─ config.py                   # constantes, rutas con pathlib, lectura de secrets/env
│  ├─ model.py                    # cargar_modelo (torch.load weights_only=True)
│  ├─ inference.py                # transforms + predecir_imagen (puro, sin Streamlit)
│  ├─ patients.py                 # load/save CSV atómico, validaciones, búsqueda
│  ├─ report.py                   # create_report_content (HTML)
│  ├─ auth.py                     # verificación de contraseña (hmac.compare_digest)
│  ├─ chatbot.py                  # UN solo motor de respuestas
│  └─ ui/
│     ├─ styles.py                # CSS unificado (una sola copia)
│     ├─ nuevo_analisis.py        # pestaña Nuevo Análisis
│     ├─ buscar_paciente.py       # pestaña Buscar Paciente
│     ├─ sidebar_info.py          # columna izquierda
│     └─ chat_widget.py           # burbuja + caja de chat única
├─ cli/predict.py                 # CLI argparse (--image, --model), 3 clases
├─ models/modelo_cancer_mobilenet.pth   # pesos (fallback a raíz)
├─ data/
│  ├─ patient_records.csv         # REAL (ignorado por .gitignore)
│  └─ sample_patient_records.csv  # 5 filas ficticias (versionado)
├─ tests/
│  ├─ test_characterization.py    # caracterización (código original/refactor)
│  ├─ test_hopescan.py            # unidad src/hopescan
│  └─ test_smoke_apptest.py       # flujo UX con streamlit.testing.AppTest
├─ docs/ (AUDITORIA.md, DECISIONES.md, ARQUITECTURA.md)
├─ .github/workflows/ci.yml
├─ requirements.txt, requirements-dev.txt, .env.example, .gitignore, README.md
```

## Flujo de datos

1. **Entrada**: Usuario llena formulario (validación: nombres/apellidos no vacíos, edad 0–120, DUI obligatorio ≥18 con formato `########-#`).
2. **Imagen**: Se abre con PIL, se convierte a RGB, se aplica `Resize(224)` + `Normalize(ImageNet)` y `ToTensor()`.
3. **Inferencia**: MobileNetV2 con `Linear(1280, 3)` + softmax → clase y probabilidades (suman ~1).
4. **Persistencia**: Registro atómico a `data/patient_records.csv` (escribir a temp + `os.replace`), DUI como string, `current_dui` evita duplicados en reruns.
5. **Reporte**: HTML descargable con imagen en base64, probabilidades, recomendación y aviso médico prominente.
6. **Búsqueda**: Protegida con contraseña (`st.secrets`/`SEARCH_PASSWORD`/`SALUD123` fallback, `hmac.compare_digest`).
7. **Chatbot**: Motor único `responder()` con reglas tolerantes a tildes/mayúsculas, burbuja y caja únicas.

## Decisiones clave (ver docs/DECISIONES.md)

- Modelo entrenado con 3 clases (`classifier.1.weight` = `(3, 1280)`); `inferencia_cancer2.py` usaba 2 (desalineado).
- `torch.load(..., weights_only=True)` verificado y mantenido.
- Nombre del producto unificado internamente como `APP_NAME = "HopeScan"`.
- `patient_records.csv` (datos reales, incluidos menores) sacado del control de versiones.
