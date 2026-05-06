from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist
from skimage.color import rgb2lab


def validate_palette_rows(rows: list[dict]) -> None:
    if not rows:
        raise ValueError("LDraw palette must contain at least one color.")
    seen_ids: set[int] = set()
    for index, row in enumerate(rows):
        if not isinstance(row.get("id"), int):
            raise ValueError(f"Palette row {index} must contain an integer id.")
        if row["id"] in seen_ids:
            raise ValueError(f"Duplicate LDraw color id: {row['id']}")
        seen_ids.add(row["id"])
        if not isinstance(row.get("name"), str) or not row["name"].strip():
            raise ValueError(f"Palette row {index} must contain a non-empty name.")
        rgb = row.get("rgb")
        if not isinstance(rgb, list | tuple) or len(rgb) != 3:
            raise ValueError(f"Palette row {index} must contain an RGB triplet.")
        if any(not isinstance(channel, int) or channel < 0 or channel > 255 for channel in rgb):
            raise ValueError(f"Palette row {index} RGB channels must be integers in [0, 255].")


def load_ldraw_palette(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open("r", encoding="utf-8") as file:
        rows = json.load(file)
    validate_palette_rows(rows)
    ids = np.asarray([row["id"] for row in rows], dtype=np.int32)
    rgb = np.asarray([row["rgb"] for row in rows], dtype=np.uint8)
    return ids, rgb


def quantize_rgb_to_ldraw(rgb: np.ndarray, palette_ids: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    if rgb.shape[-1:] != (3,):
        raise ValueError("RGB input must have a final channel dimension of size 3.")
    if palette_ids.ndim != 1:
        raise ValueError("Palette ids must be a 1D array.")
    if palette_rgb.shape != (len(palette_ids), 3):
        raise ValueError("Palette RGB values must have shape (len(palette_ids), 3).")
    flat = rgb.reshape(-1, 3).astype(np.float32) / 255.0
    palette = palette_rgb.astype(np.float32).reshape(1, -1, 3) / 255.0
    flat_lab = rgb2lab(flat.reshape(1, -1, 3)).reshape(-1, 3)
    palette_lab = rgb2lab(palette).reshape(-1, 3)
    nearest = cdist(flat_lab, palette_lab).argmin(axis=1)
    return palette_ids[nearest].reshape(rgb.shape[:-1])
