from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.spatial.distance import cdist
from skimage.color import rgb2lab


def load_ldraw_palette(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with path.open("r", encoding="utf-8") as file:
        rows = json.load(file)
    ids = np.asarray([row["id"] for row in rows], dtype=np.int32)
    rgb = np.asarray([row["rgb"] for row in rows], dtype=np.uint8)
    return ids, rgb


def quantize_rgb_to_ldraw(rgb: np.ndarray, palette_ids: np.ndarray, palette_rgb: np.ndarray) -> np.ndarray:
    flat = rgb.reshape(-1, 3).astype(np.float32) / 255.0
    palette = palette_rgb.astype(np.float32).reshape(-1, 1, 3) / 255.0
    flat_lab = rgb2lab(flat.reshape(1, -1, 3)).reshape(-1, 3)
    palette_lab = rgb2lab(palette).reshape(-1, 3)
    nearest = cdist(flat_lab, palette_lab).argmin(axis=1)
    return palette_ids[nearest].reshape(rgb.shape[:-1])

