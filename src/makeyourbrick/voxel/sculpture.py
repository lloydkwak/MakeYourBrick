from __future__ import annotations

from typing import Literal

import numpy as np

SCULPTURE_MODES = ("solid", "shell")
SculptureMode = Literal["solid", "shell"]


def validate_sculpture_options(mode: str, wall_thickness: int, base_thickness: int) -> None:
    if mode not in SCULPTURE_MODES:
        raise ValueError(f"Unsupported sculpture mode: {mode}")
    if wall_thickness < 1:
        raise ValueError("wall_thickness must be at least 1.")
    if base_thickness < 0:
        raise ValueError("base_thickness must be non-negative.")


def surface_mask(occupancy: np.ndarray) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    padded = np.pad(occupancy.astype(bool), 1, mode="constant", constant_values=False)
    interior = occupancy.astype(bool).copy()
    for dx, dy, dz in (
        (-1, 0, 0),
        (1, 0, 0),
        (0, -1, 0),
        (0, 1, 0),
        (0, 0, -1),
        (0, 0, 1),
    ):
        neighbor = padded[
            1 + dx : 1 + dx + occupancy.shape[0],
            1 + dy : 1 + dy + occupancy.shape[1],
            1 + dz : 1 + dz + occupancy.shape[2],
        ]
        interior &= neighbor
    return occupancy.astype(bool) & ~interior


def dilate_within_occupancy(seed: np.ndarray, occupancy: np.ndarray, iterations: int) -> np.ndarray:
    result = seed.astype(bool) & occupancy.astype(bool)
    for _ in range(max(0, iterations)):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        expanded = result.copy()
        for dx, dy, dz in (
            (-1, 0, 0),
            (1, 0, 0),
            (0, -1, 0),
            (0, 1, 0),
            (0, 0, -1),
            (0, 0, 1),
        ):
            expanded |= padded[
                1 + dx : 1 + dx + occupancy.shape[0],
                1 + dy : 1 + dy + occupancy.shape[1],
                1 + dz : 1 + dz + occupancy.shape[2],
            ]
        result = expanded & occupancy
    return result


def base_fill_mask(occupancy: np.ndarray, base_thickness: int) -> np.ndarray:
    base = np.zeros_like(occupancy, dtype=bool)
    if base_thickness <= 0 or occupancy.size == 0:
        return base
    max_y = min(base_thickness, occupancy.shape[1])
    base[:, :max_y, :] = occupancy[:, :max_y, :]
    return base


def apply_sculpture_mode(
    occupancy: np.ndarray,
    color_ids: np.ndarray,
    *,
    mode: SculptureMode = "solid",
    wall_thickness: int = 1,
    base_thickness: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    validate_sculpture_options(mode, wall_thickness, base_thickness)
    if color_ids.shape != occupancy.shape:
        raise ValueError("Color id array must have the same shape as occupancy.")
    occupancy = occupancy.astype(bool)
    if mode == "solid":
        return occupancy.copy(), color_ids.copy()

    shell = dilate_within_occupancy(surface_mask(occupancy), occupancy, wall_thickness - 1)
    retained = shell | base_fill_mask(occupancy, base_thickness)
    retained_colors = color_ids.copy()
    retained_colors[~retained] = 0
    return retained, retained_colors
