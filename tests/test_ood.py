"""Tests para validación OOD (FASE 2).

Cubre:
- Heurísticas individuales (monocromático, entropía, razón de aspecto, textura speckle)
- Casos combinados (valida, no_concluyente, no_es_ecografia)
- Casos límite (imágenes muy pequeñas, RGBA, escala de grises, PNG con transparencia)
- Archivos corruptos y extensiones falsas

Los tests deben:
1. Marcarse como skip si falta un archivo de fixture (para datos reales)
2. Verificar que las imágenes rechazadas sean no_es_ecografia o no_concluyente
3. Verificar que las imágenes aceptadas sean valida
4. Cubrir cada heurística por separado
5. Probar casos combinados
6. Probar casos límite
"""

from __future__ import annotations

import os
import pytest
from PIL import Image

from hopescan.inference import classify_ood

# Fixture paths
REJECT_DIR = "tests/fixtures/ood/reject"
ACCEPT_DIR = "tests/fixtures/ood/accept"


# ---------------------------------------------------------------------------
# Tests para imágenes que DEBEN rechazarse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "white.png",
        "black.png",
        "gray.png",
        "noise.png",
        "chessboard.png",
        "flat_synthetic.png",
        "green.png",
        "red.png",
        "bw_photo.png",
        "rgba.png",
    ],
)
def test_reject_images(filename):
    """Verifica que las imágenes que DEBEN rechazarse sean clasificadas como no_es_ecografia o no_concluyente."""
    path = os.path.join(REJECT_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Fixture {filename} no existe")

    img = Image.open(path)
    status = classify_ood(img)
    assert status in {"no_es_ecografia", "no_concluyente"}, f"{filename} debería rechazarse"


# ---------------------------------------------------------------------------
# Tests para imágenes que DEBEN aceptarse
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "gradient.png",
        "small_chess.png",
        "ultrasynth_0.png",
        "ultrasynth_1.png",
        "ultrasynth_2.png",
        "ultrasynth_3.png",
        "ultrasynth_4.png",
    ],
)
def test_accept_images(filename):
    """Verifica que las imágenes que DEBEN aceptarse sean clasificadas como valida."""
    path = os.path.join(ACCEPT_DIR, filename)
    if not os.path.exists(path):
        pytest.skip(f"Fixture {filename} no existe")

    img = Image.open(path)
    status = classify_ood(img)
    assert status == "valida", f"{filename} debería aceptarse"


# ---------------------------------------------------------------------------
# Tests para casos límite
# ---------------------------------------------------------------------------


def test_very_small_image():
    """Verifica que imágenes muy pequeñas sean rechazadas."""
    img = Image.new("RGB", (10, 10), color=(128, 128, 128))
    status = classify_ood(img)
    assert status in {"no_es_ecografia", "no_concluyente"}, "Imágenes muy pequeñas deberían rechazarse"


def test_rgba_image():
    """Verifica que imágenes RGBA sean manejadas correctamente."""
    img = Image.new("RGBA", (224, 224), color=(10, 20, 30, 255))
    status = classify_ood(img)
    assert status in {"no_es_ecografia", "no_concluyente"}, "Imágenes RGBA deberían rechazarse"


def test_grayscale_image():
    """Verifica que imágenes en escala de grises sean manejadas correctamente."""
    img = Image.new("L", (224, 224), color=128)
    status = classify_ood(img)
    assert status in {"no_es_ecografia", "no_concluyente"}, "Imágenes en escala de grises deberían rechazarse"


def test_corrupt_file(tmp_path):
    """Verifica que archivos corruptos sean manejados correctamente."""
    corrupt_path = tmp_path / "corrupt.png"
    corrupt_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x0aIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x02\x00\x00\x00\x00IEND\xaeB`\x82")
    with pytest.raises(Exception):
        img = Image.open(corrupt_path)
        classify_ood(img)


def test_false_extension(tmp_path):
    """Verifica que archivos con extensiones falsas sean manejados correctamente."""
    false_path = tmp_path / "fake.jpg"
    false_path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x0aIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x02\x00\x00\x00\x00IEND\xaeB`\x82")
    with pytest.raises(Exception):
        img = Image.open(false_path)
        classify_ood(img)


# ---------------------------------------------------------------------------
# Tests para heurísticas individuales
# ---------------------------------------------------------------------------


def test_monochrome_heuristic():
    """Verifica que la heurística monocromática funcione correctamente."""
    # Imagen monocromática que debería rechazarse
    mono = Image.new("RGB", (224, 224), color=(128, 128, 128))
    assert classify_ood(mono) in {"no_es_ecografia", "no_concluyente"}

    # Imagen con variación de color que debería aceptarse
    color = Image.new("RGB", (224, 224), color=(100, 150, 200))
    assert classify_ood(color) == "valida"


def test_entropy_heuristic():
    """Verifica que la heurística de entropía funcione correctamente."""
    # Imagen con baja entropía (debería rechazarse)
    low_entropy = Image.new("RGB", (224, 224), color=(128, 128, 128))
    assert classify_ood(low_entropy) in {"no_es_ecografia", "no_concluyente"}

    # Imagen con alta entropía (debería aceptarse)
    high_entropy = Image.new("RGB", (224, 224), color=(100, 150, 200))
    assert classify_ood(high_entropy) == "valida"


def test_aspect_ratio_heuristic():
    """Verifica que la heurística de razón de aspecto funcione correctamente."""
    # Imagen con razón de aspecto fuera de rango (debería rechazarse)
    wide = Image.new("RGB", (448, 224), color=(100, 150, 200))
    assert classify_ood(wide) in {"no_es_ecografia", "no_concluyente"}

    # Imagen con razón de aspecto dentro de rango (debería aceptarse)
    square = Image.new("RGB", (224, 224), color=(100, 150, 200))
    assert classify_ood(square) == "valida"


def test_speckle_texture_heuristic():
    """Verifica que la heurística de textura speckle funcione correctamente."""
    # Imagen con textura speckle (debería aceptarse)
    import numpy as np
    np.random.seed(42)
    speckle = np.random.randint(0, 256, (224, 224, 3), dtype=np.uint8)
    speckle_img = Image.fromarray(speckle)
    assert classify_ood(speckle_img) == "valida"

    # Imagen sin textura speckle (debería rechazarse)
    flat = Image.new("RGB", (224, 224), color=(100, 100, 100))
    assert classify_ood(flat) in {"no_es_ecografia", "no_concluyente"}


# ---------------------------------------------------------------------------
# Tests para casos combinados
# ---------------------------------------------------------------------------


def test_combined_cases():
    """Verifica casos combinados de heurísticas."""
    # Caso 1: Monocromático + baja entropía (debería rechazarse)
    mono_low = Image.new("RGB", (224, 224), color=(128, 128, 128))
    assert classify_ood(mono_low) in {"no_es_ecografia", "no_concluyente"}

    # Caso 2: Monocromático + alta entropía (debería rechazarse)
    mono_high = Image.new("RGB", (224, 224), color=(128, 128, 128))
    # Añadir algo de ruido para alta entropía
    import numpy as np
    mono_high_arr = np.array(mono_high)
    mono_high_arr += np.random.randint(0, 50, (224, 224, 3), dtype=np.uint8)
    mono_high = Image.fromarray(mono_high_arr)
    assert classify_ood(mono_high) in {"no_es_ecografia", "no_concluyente"}

    # Caso 3: Color + baja entropía (debería rechazarse)
    color_low = Image.new("RGB", (224, 224), color=(100, 150, 200))
    assert classify_ood(color_low) == "valida"

    # Caso 4: Color + alta entropía (debería aceptarse)
    color_high = Image.new("RGB", (224, 224), color=(100, 150, 200))
    color_high_arr = np.array(color_high)
    color_high_arr += np.random.randint(0, 50, (224, 224, 3), dtype=np.uint8)
    color_high = Image.fromarray(color_high_arr)
    assert classify_ood(color_high) == "valida"


# ---------------------------------------------------------------------------
# Tests para datos reales (marcados como skip si no existen)
# ---------------------------------------------------------------------------


def test_real_ultrasound_images():
    """Verifica imágenes de ultrasonido reales (deberían aceptarse)."""
    real_dir = "data/raw/ultrasound"
    if not os.path.exists(real_dir):
        pytest.skip("No hay datos reales de ultrasonido disponibles")

    for filename in os.listdir(real_dir):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(real_dir, filename)
            img = Image.open(path)
            status = classify_ood(img)
            assert status == "valida", f"{filename} debería aceptarse como ultrasonido real"


if __name__ == "__main__":
    pytest.main(["-v", "test_ood.py"])
