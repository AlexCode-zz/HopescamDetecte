# OOD Test Fixtures for HopeScan

This directory contains test images organized by expected OOD classification:

## Directory Structure

```
tests/fixtures/ood/
├── accept/      # Images that should be classified as "valida"
└── reject/      # Images that should be classified as "no_es_ecografia" or "no_concluyente"
```

## Image Categories

### `reject/` — Should be rejected (not valid ultrasounds)

- **white.png** — Pure white image (low entropy, low variance between channels)
- **black.png** — Pure black image
- **gray.png** — Solid gray image (monochrome-like)
- **noise.png** — Gaussian noise (low structure)
- **chessboard.png** — High-contrast chess pattern (fails speckle/texture check)
- **rgba.png** — RGBA image with alpha channel (will be converted to RGB)
- **green.png** — Solid green (unlikely ultrasound color distribution)
- **red.png** — Solid red (unlikely ultrasound color distribution)

### `accept/` — Should pass OOD validation (valid-ish ultrasounds)

- **gradient.png** — Color gradient (moderate entropy, some texture variation)
- **small_chess.png** — Large-check chessboard (may pass aspect ratio, low texture strength)
- **rgba_converted.png** — RGBA converted to RGB (valid after conversion)
- **gray_converted.png** — Grayscale converted to RGB (valid after conversion)
- **plain_rgb.png** — Plain RGB color (may pass depending on heuristics)
- **small_chess.png** — Small check pattern (different from full-chessboard)

## Usage in Tests

Tests should:

1. **Mark as skip** if the fixture file does not exist (for real patient data)
2. **Assert classification** — reject images should be `no_es_ecografia` or `no_concluyente`
3. **Assert classification** — accept images should be `valida`
4. **Cover each heuristic separately** — monochrome, entropy, aspect ratio, speckle texture
5. **Test combined cases** — "valida", "no_concluyente", "no_es_ecografia"
6. **Edge cases** — very small images, RGBA, single-channel grayscale, PNG with transparency, corrupt files, false extensions

## Real Data Note

Real ultrasound images (BUSI dataset, etc.) should be placed in `data/raw/` if available.
If no real ultrasound data exists, tests for real images should be marked as skip
with a clear message indicating the missing data path.

## Test Coverage Goals

- Each heuristic tested independently
- Combined heuristic scenarios
- Edge cases (small, RGBA, grayscale, corrupt, false extension)
- CI should fail if a reject-image is misclassified as `valida`