# Progreso del Proyecto HopeScan

## Fases y Pasos

| Fase | Descripción | Estado | Fecha | Notas |
| :--- | :--- | :--- | :--- | :--- |
| Fase 1 | Higiene, dependencias y estabilidad | Hecho | 2026-11-03 | Dependencias reparadas; secretos sin fallback; CI y `.gitignore` actualizados. |
| Fase 2 | Validación OOD | Hecho (provisional) | 2026-11-03 | Heurísticas + energy score; estados seguros y tests. Falta calibrar con datos reales. |
| Fase 3 | Entrenamiento reproducible | Pendiente | - | Requiere dataset validado (p. ej. BUSI) y GPU/entorno de entrenamiento. |
| Fase 4 | Chatbot con RAG | Hecho | 2026-11-03 | TF-IDF local, citas, guardrails y Claude opcional. Documentos de ejemplo. |
| Fase 5 | Funciones nuevas | Hecho | 2026-11-03 | Grad-CAM, modo demostración, reporte HTML seguro y búsqueda con DUI enmascarado. |
| Fase 6 | Diseño y UX | Hecho | 2026-11-03 | Tema nativo rosa/magenta, tarjetas, badges, pasos y chat nativo. |
| Fase 7 | Seguridad y calidad | Hecho (parcial) | 2026-11-03 | `weights_only=True`, escape HTML, `compare_digest`, límite de intentos y tests. Falta purgar el historial. |
| Fase 8 | Purga del historial de Git | Hecho | 2026-11-03 | Historial reescrito con `git filter-repo` y force-push a main y refactor/estructura-y-estabilidad. Ver `docs/LIMPIEZA_HISTORIAL.md`. |

## Último comando de prueba exitoso

```bash
.venv/bin/python -m pytest tests/ -q
# 107 passed
```

Lint y formato:

```bash
.venv/bin/python -m ruff check src/ app.py inferencia_cancer3.py cli/ tests/
.venv/bin/python -m ruff format --check src/ app.py inferencia_cancer3.py cli/ tests/
```

## Pendientes reales

1. **Calibración OOD con datos reales.** Los umbrales actuales provienen de
   fixtures sintéticos. `models/ood_calibration.json` deja las métricas en `null`
   a propósito. Sin un conjunto etiquetado no se puede afirmar sensibilidad,
   especificidad ni ECE.
2. **Validación clínica externa.** El modelo no es un dispositivo médico.
3. **Solicitar GC de objetos inalcanzables a GitHub.** El historial fue purgado, pero el SHA antiguo `5cd0be5` puede seguir sirviendo el archivo temporalmente hasta que GitHub ejecute garbage collection. Tratarse los datos como expuestos.
4. **Sustituir los documentos de `rag/knowledge/`** por fuentes oficiales
   (OMS, ACS, NCI, MINSAL) antes de un uso real del chat.
5. **Exportación nativa a PDF** y autenticación por roles, si el proyecto crece.
