"""CLI de inferencia para HopeScan.

Reemplazo de ``inferencia_cancer2.py`` (que usaba rutas absolutas de Windows y
clasificador de 2 clases). Reutiliza ``inference.py`` y las 3 clases correctas
(``["Benigno", "Maligno", "Normal"]``) sin rutas hardcodeadas de Windows.

Uso:
    python -m cli.predict --image foto.png --model models/modelo_cancer_mobilenet.pth
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # raíz del proyecto

import torch
from PIL import Image

from src.hopescan.inference import predict_image
from src.hopescan.model import build_mobilenet_classifier, load_model
from src.hopescan.config import CLASSES, MOBILENET_V2_FEATURES, NUM_CLASSES


def predict_from_args(args: argparse.Namespace) -> dict:
    """Ejecuta inferencia con argparse args."""
    model_path = Path(args.model) if args.model else None
    image_path = Path(args.image)

    if not image_path.exists():
        print(f"❌ ERROR: No encuentro la imagen en: {image_path}")
        return {"error": "image_not_found"}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"⚙️  Usando dispositivo: {device}")

    try:
        model = build_mobilenet_classifier()
        sd_path = model_path if (model_path and model_path.exists()) else None
        if sd_path:
            state_dict = torch.load(sd_path, map_location=device, weights_only=True)
            model.load_state_dict(state_dict)
        else:
            # Fallback al path resuelto del config
            from src.hopescan.config import resolve_model_path
            resolved = resolve_model_path()
            if resolved:
                model.load_state_dict(torch.load(resolved, map_location=device, weights_only=True))
            else:
                raise FileNotFoundError("No se encontró el modelo")
    except Exception as exc:
        print(f"❌ Error cargando el modelo: {exc}")
        return {"error": str(exc)}

    model.to(device).eval()

    try:
        img = Image.open(image_path).convert("RGB")
        pred_idx, probs = predict_image(model, device, img)
    except Exception as exc:
        print(f"❌ Error procesando la imagen: {exc}")
        return {"error": str(exc)}

    if pred_idx is None:
        print("❌ No se pudo obtener el diagnóstico.")
        return {"error": "prediction_failed"}

    resultado = CLASSES[pred_idx]
    confianza = probs[pred_idx] * 100

    print("\n" + "=" * 30)
    print(f"🩺 RESULTADO DEL DIAGNÓSTICO")
    print("=" * 30)
    print(f"📂 Imagen: {image_path.name}")
    print(f"🦠 Predicción: {resultado.upper()}")
    print(f"📊 Confianza: {confianza:.2f}%")
    print("📊 Distribución:")
    for cls, p in zip(CLASSES, probs):
        print(f"   {cls}: {p * 100:.2f}%")
    print("=" * 30 + "\n")
    return {"result": resultado, "confidence": confianza, "probabilities": probs}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="HopeScan CLI — análisis de ultrasonido de mama (MobileNetV2)"
    )
    parser.add_argument("--image", required=True, help="Ruta a la imagen de ultrasonido")
    parser.add_argument("--model", default=None,
                        help="Ruta al .pth (default: models/modelo_cancer_mobilenet.pth)")
    args = parser.parse_args()
    predict_from_args(args)


if __name__ == "__main__":
    main()
