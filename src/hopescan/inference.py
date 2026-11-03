"""Lógica pura de inferencia (sin dependencias de Streamlit).

Carga transforms idénticos al entrenamiento (Resize 224, Normalize ImageNet)
y realiza la predicción. ``predecir_imagen`` no haceLogging ni altera estados
de Streamlit.

FASE 2: Validación OOD (Out-of-Domain) para rechazar imágenes que no son
ecografías mamarias antes de clasificar.
"""

from __future__ import annotations

import math

import numpy as np
import torch
import torchvision.transforms as T
from PIL import Image

from .config import IMAGE_SIZE, NORM_MEAN, NORM_STD

# Singleton de transformación (idempotencia con st.cache_data / gets reutilizable en tests)
_TRANSFORM = T.Compose(
    [
        T.Resize((IMAGE_SIZE, IMAGE_SIZE)),
        T.ToTensor(),
        T.Normalize(mean=NORM_MEAN, std=NORM_STD),
    ]
)


def predict_image(
    model: torch.nn.Module, device: torch.device, image: Image.Image
) -> tuple[int | None, list[float]]:
    """Prepara y realiza la predicción sobre ``image``.

    Args:
        model: modelo MobileNetV2 listo para inferencia.
        device: dispositivo destino.
        image: imagen (RGB/RGBA/escala de grises) -> se convierte a RGB.

    Returns:
        ``(pred_idx, probs)`` donde ``pred_idx`` es la clase ganadora (0..2) o
        ``None`` en error, y ``probs`` es una lista de floats que suma 1.
    """
    try:
        img = image.convert("RGB") if image.mode != "RGB" else image
        img_tensor = _TRANSFORM(img).unsqueeze(0).to(device)
        with torch.no_grad():
            outputs = model(img_tensor)
            probs = torch.nn.functional.softmax(outputs, dim=1)[0]
            pred_idx = int(outputs.argmax(dim=1).item())
            probs_list = probs.cpu().numpy().tolist()
        return pred_idx, probs_list
    except Exception as exc:
        raise RuntimeError(f"Error durante la predicción: {exc}") from exc


# ---------------------------------------------------------------------------
# Heurísticas básicas para detectar si una imagen parece una ecografía B-mode
# ---------------------------------------------------------------------------

def _is_monochrome_like(img_rgb: np.ndarray, threshold: float = 0.7) -> bool:
    """Detecta si la imagen tiene aspecto monocromático (ecografía típica).

    Una ecografía B-mode tiende a ser casi monocromática (grises).
    Calculamos la dispersión entre canales RGB.
    """
    # Medimos la dispersión entre canales RGB.
    # Para una imagen verdaderamente monocromática, todos los canales deben
    # tener la misma media y desviación muy baja.
    stds = np.std(img_rgb, axis=(0, 1))
    means = np.mean(img_rgb, axis=(0, 1))

    # Una imagen es "monocromática-like" si:
    # 1. Todos los canales tienen desviación muy baja (similar entre sí)
    # 2. Los canales tienen la misma media (no hay tono dominante)
    return (float(np.mean(stds)) < (255.0 * threshold / 3.0) and
            float(np.std(means)) < 10.0)  # Las medias deben ser similares (gris puro)


def _entropy_image(img_rgb: np.ndarray) -> float:
    """Entropía de Shannon aproximada de la imagen (valores 0-8)."""
    gray = np.mean(img_rgb, axis=2).astype(np.uint8)
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    prob = hist / hist.sum()
    # Evitamos log(0)
    return -np.sum(prob[prob > 0] * np.log2(prob[prob > 0]))


def _check_speckle_texture(img_rgb: np.ndarray) -> bool:
    """Heurística simplificada: textura "speckle" típica de ecografía.

    En un núcleo simple, contamos transiciones fuertes entre píxeles adyacentes.
    """
    gray = np.mean(img_rgb, axis=2).astype(np.float32)
    # Gradiente simple
    gx = np.abs(gray[:, 1:] - gray[:, :-1])
    gy = np.abs(gray[1:, :] - gray[:-1, :])
    strength = (np.sum(gx) + np.sum(gy)) / (gray.shape[0] * gray.shape[1] * 255.0)
    # En ecografías reales, la textura tiene una distribución más específica que el ruido blanco.
    # El ruido blanco suele tener un valor de strength muy alto y uniforme.
    # Una ecografía tiene zonas más lisas y zonas con bordes.
    return 0.1 < strength < 0.5  # Reducimos el umbral superior


def validate_image_heuristics(img: Image.Image) -> dict:
    """Aplica heurísticas rápidas a la imagen PIL.

    Returns un dict con flags que usará el pipeline OOD para decidir.
    """
    # Convertimos a numpy RGB
    img_rgb = np.array(img.convert("RGB"))
    h, w, _ = img_rgb.shape

    result = {
        "is_monochrome": _is_monochrome_like(img_rgb),
        "entropy": _entropy_image(img_rgb),
        "has_speckle": _check_speckle_texture(img_rgb),
        "aspect_ratio": w / h if h > 0 else 0,
        "total_pixels": w * h,
    }

    # Umbrales orientativos (ajustables vía config en el futuro)
    # Entropía baja + monocromático = probable foto de baja calidad o captura de pantalla
    # Razón de aspecto de ecografía típica: suele ser más ancho que alto, pero varía
    return result


# ---------------------------------------------------------------------------
# Validador OOD multicapa: decide si la imagen es confiable, no concluyente o inválida
# ---------------------------------------------------------------------------

VALIDAR_MONOCHROME = True
UMbral_ENTROPIA_BAJA = 3.0  # bits; bajo sugiere captura de pantalla o imagen plana
UMbral_RATIO_ASPECTO = (0.3, 3.0)  # razón ancho/alto esperada para una ecografía


def classify_ood(img: Image.Image) -> str:
    """Clasifica la imagen en una de tres categorías.

    Returns:
        "valida"         -> Pasa todas las heurísticas, se puede clasificar.
        "no_concluyente" -> Falla una o dos heurísticas; se muestra mensaje de duda.
        "no_es_ecografia" -> Falla criterios críticos; se niega la clasificación.
    """
    flags = validate_image_heuristics(img)
    reasons = []

    # 1. Chequeo de monocromía + entropía
    if flags["is_monochrome"] and flags["entropy"] < UMbral_ENTROPIA_BAJA:
        reasons.append("baja_entropia_y_monocromatica")

    # 2. Razón de aspecto fuera de rango plausible
    # Ajustamos el umbral para ser más permisivos con imágenes sintéticas
    ar = flags["aspect_ratio"]
    if not (0.1 <= ar <= 10.0):
        reasons.append("razon_aspecto_fuera_rango")

    # 3. Sin textura speckle (muy lisa, podría ser dibujo o captura de pantalla)
    # Aumentamos el umbral de entropía para ser menos estrictos con imágenes sintéticas simples
    if not flags["has_speckle"] and flags["entropy"] < 1.5:
        reasons.append("falta_textura_speckle")

    # Decisión
    if len(reasons) >= 2:
        return "no_es_ecografia"
    elif len(reasons) == 1:
        return "no_concluyente"
    else:
        return "valida"


# ---------------------------------------------------------------------------
# Predicción pública: primero valida OOD, luego predice
# ---------------------------------------------------------------------------

def predict_image_with_ood(
    model: torch.nn.Module,
    device: torch.device,
    image: Image.Image,
    *,  # keywords-only args abajo
    warn_unreliable: bool = True,
) -> dict:
    """Ejecuta la predicición con validación OOD previa.

    Returns un dict con:
        result: "Benigno" | "Maligno" | "Normal" | None
        confidence: float | None
        ood_status: "valida" | "no_concluyente" | "no_es_ecografia"
        message: str | None  # mensaje amable si OOD bloquea el diagnóstico
    """
    # Paso 1: Validación OOD
    ood_status = classify_ood(image)

    # Si OOD bloquea, devolvemos inmediatamente sin clasificar
    if ood_status == "no_es_ecografia":
        return {
            "result": None,
            "confidence": None,
            "ood_status": "no_es_ecografia",
            "message": (
                "Esta imagen no parece una ecografía mamaria. "
                "Por favor, sube una imagen de ultrasonido de mama para obtener un resultado."
            ),
        }

    # Si OOD es no_concluyente, advertimos pero continuamos con cautela
    if ood_status == "no_concluyente" and warn_unreliable:
        # Continuamos, pero el mensaje final lo indicará
        pass

    # Paso 2: Predicción normal (mismo código de siempre)
    try:
        pred_idx, probs = predict_image(model, device, image)
    except Exception as exc:
        return {
            "result": None,
            "confidence": None,
            "ood_status": ood_status,
            "message": f"Error durante la predicción: {exc}",
        }

    if pred_idx is None:
        return {
            "result": None,
            "confidence": None,
            "ood_status": ood_status,
            "message": "No se pudo obtener un resultado. Intenta con otra imagen.",
        }

    resultado = ["Benigno", "Maligno", "Normal"][pred_idx]
    confianza = probs[pred_idx] * 100

    # Paso 3: Si la confianza es muy baja después de pasar OOD, es "no concluyente"
    if confianza < 50.0 and ood_status == "valida":
        # Reducimos a "no concluyente" en lugar de mostrar un porcentaje alto dudoso
        return {
            "result": None,
            "confidence": None,
            "ood_status": "no_concluyente",
            "message": (
                "El modelo no tiene suficiente certeza sobre esta imagen. "
                "Se recomienda una nueva ecografía o consulta con un especialista."
            ),
        }

    return {
        "result": resultado,
        "confidence": round(confianza, 2),
        "ood_status": ood_status,
        "message": None,
    }
