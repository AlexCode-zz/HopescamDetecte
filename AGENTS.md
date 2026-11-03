# HopeScan — AGENTS.md

Compact instruction file for agents working in this repo. Only high-signal, repo-specific guidance is included.

## Entry points

- **Streamlit app**: `streamlit run app.py` (or `./run.sh` — creates venv, installs deps, copies config templates, launches at `http://localhost:8501`).
- **CLI**: `python -m cli.predict --image foto.png --model models/modelo_cancer_mobilenet.pth`
- **Legacy shim**: `inferencia_cancer3.py` (root, delegates to the same logic).
- Pure logic lives in `src/hopescan/` (no Streamlit at module level). `app.py` is the UI layer only.
- New safety pipeline: `src/hopescan/ood/` (validation + energy score), `src/hopescan/gradcam.py`, `src/hopescan/rag/` (TF-IDF retrieval, guardrails, chat).

## Python / environment

- Python 3.10+ (tested with 3.13.5).
- `.venv/` exists locally but is gitignored; use `.venv/bin/python` and `.venv/bin/python -m pytest`.
- Linux/CI: `pip install -r requirements-cpu.txt` (torch from the CPU index).
- macOS/other: `pip install -r requirements.txt`.
- Optional Claude chat: `pip install -r requirements-rag.txt`.
- Dev dependencies: `pip install -r requirements-dev.txt` (pytest, pytest-cov, ruff).

## Model and safety contract

- Weights: `modelo_cancer_mobilenet.pth` at repo root; resolution checks `models/` first, then root.
- Classes: `Benigno`, `Maligno`, `Normal`.
- Final statuses (`src/hopescan/config.py`): `valida_confiable`, `valida_no_concluyente`, `no_es_ecografia_mamaria`.
- **Never show a class, confidence or Grad-CAM unless the status is `valida_confiable`.** Invalid images must never reach the model.
- OOD combines heuristics with an energy score (`T * logsumexp(logits/T)`). Thresholds live in `models/ood_calibration.json` and are **provisional fixtures-only values**; do not present them as clinical calibration.
- `classify_ood()` runs heuristics only. `analyze_image()` runs the full pipeline (heuristics + model + calibrated confidence + energy). Tests that need the final status must use `analyze_image()`.
- Energy rule in the current fixtures: valid ultrasounds ~1.0–1.5; invalid white/black/gray ~3.9–8.1; reject when energy > 1.8. `ultrasynth_0` passes heuristics but is `valida_no_concluyente` because calibrated confidence is low.
- Fixture expectations: `tests/fixtures/ood/accept/small_chess.png` and `gradient.png` are rejected; `tests/fixtures/ood/accept/ultrasynth_1..4` are reliable; `ultrasynth_0` is non-conclusive.

## Commands (exact, verified)

Run all:
```bash
./run.sh
```

Tests:
```bash
.venv/bin/python -m pytest tests/ -q          # 107 tests, CI uses this exact form
.venv/bin/python -m pytest --cov=src/hopescan # optional coverage
```

Lint / format (CI runs both):
```bash
.venv/bin/python -m ruff check src/ app.py inferencia_cancer3.py cli/ tests/
.venv/bin/python -m ruff format --check src/ app.py inferencia_cancer3.py cli/ tests/
```

## CI

- Workflow: `.github/workflows/ci.yml`
- Triggers: push to `main` or `refactor/estructura-y-estabilidad`; PR to `main`.
- Python version: 3.13 only.
- Steps: install `requirements-cpu.txt` + `requirements-dev.txt`, `ruff check`, `ruff format --check`, `pytest tests/ -q`.

## Config & secrets

- `SEARCH_PASSWORD` is read from the environment or `st.secrets`. **There is no default password.** If it is empty or absent, the patient search is disabled.
- `.streamlit/secrets.toml.example` ships with an empty password on purpose; do not reintroduce a known placeholder such as `SALUD123`.
- Streamlit promotes `st.secrets` values to `os.environ`; configure the password in one place to avoid surprises. Tests use the effective configured password after `AppTest` loads secrets.
- Optional Claude: `ANTHROPIC_API_KEY` + `ANTHROPIC_MODEL`. Without them, the RAG works extractively with citations and makes no network calls.
- Templates: `.env.example`, `.streamlit/secrets.toml.example`. Never commit the real `.env` or `.streamlit/secrets.toml`.
- `data/patient_records.csv` (real patient data) is gitignored; `data/sample_patient_records.csv` (fictitious) is versioned.
- RAG documents in `rag/knowledge/` are examples, not validated clinical sources. Replace them before any real use.

## Data privacy and Git

- The real `patient_records.csv` was uploaded in commit `5cd0be5` of the public history. It was purged from the rewritten history (2026-11-03, `git filter-repo` + force-push to main and refactor/estructura-y-estabilidad). The old SHA may still serve the file temporarily until GitHub runs garbage collection; treat the data as exposed.
- Cleanup instructions: `docs/LIMPIEZA_HISTORIAL.md`.
- Do not commit `.env`, `.streamlit/secrets.toml`, `.venv/`, `data/patient_records.csv`, `__pycache__/`, `.pytest_cache/`.

## Branches

- Current working branch: `main`, tracking `origin/main` (clean). CI also targets `refactor/estructura-y-estabilidad`. PRs to `main` run CI.

## What to avoid

- Do not present results as a medical diagnosis or false reassurance. Prefer “no concluyente” over forcing “Benigno/Normal”.
- Do not show probabilities when the status is not `valida_confiable`.
- Do not use `use_container_width` in Streamlit (deprecated); use `width="stretch"` or `width="content"`.
- Do not add CSS unless no native Streamlit component exists; prefer `.streamlit/config.toml` for theming and native components (`st.container`, `st.badge`, `st.metric`, `st.chat_message`).
- Do not add `SALUD123`, real patient data, API keys or model weights to version control.
