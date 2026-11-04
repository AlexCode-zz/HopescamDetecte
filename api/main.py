"""HopeScan API — FastAPI backend.

Expone la lógica pura de ``src/hopescan/`` (inferencia, OOD, pacientes,
búsqueda y chat RAG) como endpoints JSON para el frontend React.

La lógica de dominio no se toca: solo se adapta a HTTP (multipart para la
imagen, JSON para el paciente y el chat).
"""

from __future__ import annotations

import base64
import io
import json
import sys
import uuid
from io import BytesIO
from pathlib import Path as _P
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel

sys.path.insert(0, str(_P(__file__).resolve().parents[1] / "src"))

from hopescan.config import (
    APP_NAME,
    CLASS_LABELS_ES,
    CLASSES,
    DEMO_IMAGE_PATH,
    is_search_enabled,
)
from hopescan.inference import analyze_image
from hopescan.model import load_model
from hopescan.ood import (
    OOD_NO_ES_ECOGRAFIA,
    OOD_VALIDA_CONFIABLE,
    OOD_VALIDA_NO_CONCLUYENTE,
)
from hopescan.patients import (
    check_dui,
    load_patient_db,
    mask_dui,
    save_patient_data,
    search_patients,
)
from hopescan.rag.chat import answer, llm_available
from hopescan.rag.guardrails import DISCLAIMER

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="HopeScan API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Estado del modelo (cargado una vez)
# ---------------------------------------------------------------------------

_model = None
_device = None
_model_error: str | None = None


def _ensure_model() -> tuple[Any, Any]:
    global _model, _device, _model_error
    if _model is None and _model_error is None:
        try:
            _model, _device = load_model()
            if _model is None:
                _model_error = "No se encontró el archivo de pesos del modelo."
        except Exception as exc:  # noqa: BLE001 — no caer la app por el modelo
            _model_error = str(exc)
            _model = None
            _device = None
    return _model, _device


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def _image_to_b64(image: Image.Image, fmt: str = "JPEG", quality: int = 90) -> str:
    buffer = BytesIO()
    image.save(buffer, format=fmt, quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def _serialize_result(result: dict[str, Any]) -> dict[str, Any]:
    """Convierte el dict de analyze_image en una respuesta JSON limpia."""
    status = result.get("status")
    result_class = result.get("result")
    confidence = result.get("confidence")
    probabilities = result.get("probabilities_percent") or []

    probs = []
    for cls, value in zip(CLASSES, probabilities):
        probs.append(
            {
                "class": cls,
                "label": CLASS_LABELS_ES.get(cls, cls),
                "probability": round(float(value), 2),
            }
        )

    return {
        "status": status,
        "can_show_class": status == OOD_VALIDA_CONFIABLE,
        "result": result_class,
        "result_label": CLASS_LABELS_ES.get(result_class, result_class),
        "confidence": confidence,
        "confidence_text": f"{float(confidence):.1f}%"
        if confidence is not None
        else None,
        "probabilities": probs,
        "margin": result.get("margin"),
        "energy": result.get("energy"),
        "temperature": result.get("temperature"),
        "reasons": result.get("reasons") or [],
        "features": result.get("features") or {},
        "message": result.get("message"),
        "image_b64": result.get("image_b64"),
        "gradcam_b64": result.get("gradcam_b64"),
        "calibration": result.get("calibration") or {},
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    model, _ = _ensure_model()
    return {
        "ok": True,
        "app": APP_NAME,
        "model_ready": model is not None,
        "model_error": _model_error,
        "search_enabled": is_search_enabled(),
        "chat_available": llm_available(),
    }


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),  # noqa: B008 — patrón estándar de FastAPI
    patient_data: str = Form("{}"),
    demo_mode: str = Form("false"),
    with_gradcam: str = Form("true"),
) -> JSONResponse:
    """Ejecuta el pipeline completo de análisis (OOD + modelo + Grad-CAM).

    Recibe la imagen como archivo multipart y los datos del paciente como
    JSON string. Devuelve el resultado serializado; las imágenes van en
    base64 dentro del JSON.
    """
    model, device = _ensure_model()
    if model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_model_error or "Modelo no disponible.",
        )

    # Leer imagen.
    image_bytes = await image.read()
    try:
        pil_image = Image.open(io.BytesIO(image_bytes))
        pil_image.load()
    except Exception as exc:  # noqa: BLE001 — error controlado hacia el cliente
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se pudo leer la imagen: {exc}",
        )

    # Datos del paciente.
    try:
        patient = json.loads(patient_data) if patient_data.strip() else {}
    except json.JSONDecodeError:
        patient = {}
    demo = demo_mode.strip().lower() in {"1", "true", "si", "sí", "yes"}
    with_gradcam_flag = with_gradcam.strip().lower() in {"1", "true", "si", "sí", "yes"}

    # Ejecutar pipeline.
    try:
        result = analyze_image(model, device, pil_image, with_gradcam=with_gradcam_flag)
    except Exception as exc:  # noqa: BLE001 — la UI recibe un error controlado
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": OOD_VALIDA_NO_CONCLUYENTE,
                "can_show_class": False,
                "message": f"No se pudo analizar la imagen: {exc}",
                "reasons": ["error_inferencia"],
            },
        )

    # Serializar e incrustar imágenes en base64.
    result["image_b64"] = _image_to_b64(pil_image)
    if result.get("gradcam") is not None:
        result["gradcam_b64"] = _image_to_b64(result["gradcam"])
    # No enviar el objeto PIL ni el tensor al cliente.
    result.pop("gradcam", None)

    payload = _serialize_result(result)

    # Guardar registro si corresponde (nunca en demo, nunca si imagen inválida).
    if (
        not demo
        and payload["status"] != OOD_NO_ES_ECOGRAFIA
        and patient
        and patient.get("nombres")
        and patient.get("apellidos")
    ):
        try:
            save_patient_data(patient, result)
            payload["saved"] = True
        except Exception:  # noqa: BLE001 — no debe romper el resultado
            payload["saved"] = False
            payload["save_error"] = "No se pudo guardar en la base local."
    else:
        payload["saved"] = False

    payload["analysis_id"] = uuid.uuid4().hex
    return JSONResponse(content=payload)


# ---------------------------------------------------------------------------
# Pacientes (búsqueda protegida)
# ---------------------------------------------------------------------------

# Sesiones en memoria (por proceso). En producción se recomienda un proveedor
# de identidad real (OIDC / JWT con argon2).
_active_sessions: set[str] = set()


class LoginRequest(BaseModel):
    password: str


@app.post("/api/patients/login")
def patients_login(req: LoginRequest) -> dict[str, Any]:
    if not is_search_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La búsqueda está deshabilitada (no hay contraseña configurada).",
        )
    from hopescan.auth import verify_search_password

    if not verify_search_password(req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Contraseña incorrecta.",
        )
    token = uuid.uuid4().hex
    _active_sessions.add(token)
    return {"authenticated": True, "token": token}


@app.post("/api/patients/logout")
def patients_logout(req: LoginRequest) -> dict[str, Any]:
    _active_sessions.discard(req.password)  # password campo reutilizado como token
    return {"ok": True}


def _require_session(token: str | None) -> None:
    if not is_search_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="La búsqueda está deshabilitada.",
        )
    if not token or token not in _active_sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión de búsqueda no autenticada.",
        )


@app.get("/api/patients/search")
def patients_search(token: str | None = None, q: str = "") -> dict[str, Any]:
    _require_session(token)
    df = load_patient_db()
    results = search_patients(df, q) if q else df.head(10)

    records = []
    for _, row in results.iterrows():
        dui = str(row.get("DUI", "") or "")
        records.append(
            {
                "nombres": row.get("Nombres", ""),
                "apellidos": row.get("Apellidos", ""),
                "edad": row.get("Edad", ""),
                "genero": row.get("Género", ""),
                "dui": mask_dui(dui) if check_dui(dui) else dui,
                "fecha_registro": row.get("Fecha_Registro", ""),
                "resultado_ia": row.get("Resultado_IA", ""),
                "confianza_ia": row.get("Confianza_IA", ""),
            }
        )
    return {"results": records, "count": len(records)}


# ---------------------------------------------------------------------------
# Chat educativo (RAG)
# ---------------------------------------------------------------------------


class ChatRequest(BaseModel):
    question: str
    history: list[dict[str, str]] | None = None
    last_result: dict[str, Any] | None = None


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict[str, Any]:
    result = answer(
        req.question,
        history=req.history,
        last_result=req.last_result,
    )
    return {
        "text": result.text,
        "sources": [
            {
                "title": s.title,
                "doc_id": s.doc_id,
                "snippet": s.snippet,
                "score": s.score,
            }
            for s in result.sources
        ],
        "kind": result.kind,
        "used_llm": result.used_llm,
        "disclaimer": DISCLAIMER,
    }


@app.get("/api/demo/image")
def demo_image() -> dict[str, Any]:
    """Devuelve la ecografía sintética de demostración en base64."""
    if not DEMO_IMAGE_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Imagen de demostración no encontrada.",
        )
    img = Image.open(DEMO_IMAGE_PATH)
    img.load()
    return {
        "image_b64": _image_to_b64(img),
        "label": "Ecografía sintética de demostración",
    }


# ---------------------------------------------------------------------------
# Manejador de errores 404 amigable
# ---------------------------------------------------------------------------


@app.exception_handler(404)
async def _not_found(_, __):
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint no encontrado."},
    )
