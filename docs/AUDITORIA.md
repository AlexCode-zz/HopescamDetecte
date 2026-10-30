# Auditoria de HopeScan (HopeScamDetecte)

## Estructura actual (código original, antes del refactor)

```
HopescamDetecte/
├── inferencia_cancer2.py      # Script CLI — rutas ABSOLUTAS de Windows, 2 clases
├── inferencia_cancer3.py      # App Streamlit principal (~1070 líneas)
├── modelo_cancer_mobilenet.pth  # Pesos (~9 MB)
├── patient_records.csv        # Dato REAL e incluyen menores (violación Privacy)
├── requemens.txt              # Archivo de texto roto ("almoahada numpy")
└── README.md                  # Vacío
```

Ninguna carpeta `.git`, ningún `.gitignore`, ningún tests, ningún CI.

## Errores detectados

### Programa
- **Chatbot duplicado:** la función `responder()` se define **tres veces** (líneas 808, 1004, 1061). Las respuestas útiles están dispersas. El flujo #3 redefine variables como `chat_css` sin borrar el anterior, duplicando estilos.
- **`user_input` usado antes de definirse:** en la línea 1020 se usa `if user_input:` pero `user_input = st.chat_input(...)` está en la línea 916. Si el flujo llega más allá del botón render, TypeError. (En práctica Streamlit no llega ahí; sin embargo es un bug sutil.)
- **CSS duplicado global `st.markdown(css ...)`** define la misma cadena HTML dos veces (líneas 84 y 798).
- **`st.markdown(chat_css, ...)`** define también el CSS de la burbuja dos veces (798 y 994).
- **`predecir_imagen`** usa `st.error(...)` inside the function — la función lógica depende de `streamlit` como contexto. Viola separación de concerns.
- **Carga del modelo** usa `torch.load(MODEL_PATH)` sin `weights_only=True` → riesgo de sicurezza futuro con el dep PyTorch >= 2.0.
- **Guardado de CSV**usa `pd.concat` + `to_csv` directo → escritura concurrente / corrompimiento en updates multi-hilo.
- **CSV corrupto:** `load_patient_db` captura excepción y retorna DataFrame vacío con mensajes `st.error`, mezclando logging con UI.

### Seguridad / Privacidad
- `patient_records.csv` con datos reales incluidos menores → **datos PII en control de versiones**.
- Contraseña `SEARCH_PASSWORD = "SALUD123"` hardcodeada sin compare-digest ni fallback graceful.
- `requemens.txt` kein نظام تحديث dependencies.

### Deuda técnica
- Sin `tests/`, sin CI, sin `.gitignore`, sin `.env.example`.
- `inferencia_cancer2.py` con rutas absolutas Windows y clasificador de 2 clases (desacordo con el app de 3 clases).
- Sin type hints, sin docstrings, sin separación lógica/UI.
- El nombre del producto duplica: "HopeScam" vs "EcoScan" en títulos visibles + CSS.

## Riesgos
1. **Datos sensibles en historial git:** `patient_records.csv` fue habría estado en algún commit (no hay evidencia de commit yet; se verifica al iniciar). Debe moverse fuera del control.
2. **Modelo no certificado como dispositivo médico:** la app es apoyo, pero el aviso médico debe permanecer visible y prominente.
3. **Clasificación discrepan:** app=3 classes (Benigno/Maligno/Normal), CLI=2 classes. El `modelo_cancer_mobilenet.pth` entrenado con 3.
4. **Confianza < 60% mostrada sin alarma:** el CSV tiene 52.02% y 100.0% — se requiere hint de baja confianza sin alterar el resultado mostrado.
