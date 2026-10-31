# HopeScan — AGENTS.md

Compact instruction file for agents working in this repo. Only high-signal, repo-specific guidance is included.

## Entry points

- **Streamlit app**: `streamlit run app.py` (or `./run.sh` wrapper — creates venv, installs deps, copies config templates, launches app at `http://localhost:8501`).
- **CLI**: `python -m cli.predict --image foto.png --model models/modelo_cancer_mobilenet.pth`
- **Legacy shim**: `inferencia_cancer3.py` (root, delegates to same logic).
- Pure logic lives in `src/hopescan/` (no Streamlit at module level). `app.py` is the UI layer only.

## Python / environment

- Python 3.10+ (tested with 3.13.5).
- A `.venv/` exists locally but is gitignored; create with `python -m venv .venv` and activate.
- CI installs torch from the CPU index: `pip install -r requirements.txt --index-url https://download.pytorch.org/whl/cpu`
- Dev dependencies: `pip install -r requirements-dev.txt` (pytest, pytest-cov, ruff).

## Model

- Weights file: `modelo_cancer_mobilenet.pth` at repo root (CI/resolve checks `models/` first, then root).
- Classes: `Benigno`, `Maligno`, `Normal`.
- Confidence thresholds (in `src/hopescan/config.py`): `< 60%` warns low confidence; `< 40%` marks result unreliable.

## Commands (exact, verified)

Run all:
```bash
./run.sh
```

Tests:
```bash
pytest                    # all 38 tests
pytest tests/ -q          # CI uses this exact form
pytest --cov=src/hopescan # coverage (min ≥80% in inference, patients, chatbot, auth, report)
```

Lint / format (CI runs both):
```bash
ruff check src/ app.py inferencia_cancer3.py cli/ tests/
ruff format --check src/ app.py inferencia_cancer3.py cli/ tests/
```

## CI

- Workflow: `.github/workflows/ci.yml`
- Triggers: push to `main` or `refactor/estructura-y-estabilidad`; PR to `main`.
- Python version: 3.13 only.
- Steps: install deps (torch CPU), `ruff check`, `ruff format --check`, `pytest tests/ -q`.

## Config & secrets

- `SEARCH_PASSWORD` read in order: `st.secrets` → env var → fallback `SALUD123` (dev warning shown).
- Templates: `.env.example`, `.streamlit/secrets.toml.example`. Copy to `.env` and `.streamlit/secrets.toml` — never commit them.
- `data/patient_records.csv` (real patient data) is gitignored; `data/sample_patient_records.csv` (fictitious) is versioned.

## Branches

- Default working branch: `refactor/estructura-y-estabilidad`.
- CI also targets `main`. PRs to `main` run CI.

## What to avoid

- Do not commit `.env`, `.streamlit/secrets.toml`, `.venv/`, `data/patient_records.csv`, `__pycache__/`, `.pytest_cache/`.
- Do not use `use_container_width` in Streamlit (deprecated); use `width="stretch"` or `width="content"`.
- Do not add CSS unless no native Streamlit component exists; prefer `.streamlit/config.toml` for theming.