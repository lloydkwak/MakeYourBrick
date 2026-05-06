from __future__ import annotations

import numpy as np


def _validate_size(size: tuple[int, int, int]) -> tuple[int, int, int]:
    if len(size) != 3:
        raise ValueError("Size must contain exactly three dimensions: width, height, depth.")
    width, height, depth = (int(value) for value in size)
    if width <= 0 or height <= 0 or depth <= 0:
        raise ValueError("All voxel dimensions must be positive.")
    return width, height, depth


def make_solid_box(
    size: tuple[int, int, int],
    color_id: int = 16,
) -> tuple[np.ndarray, np.ndarray]:
    """Create a filled box as `(occupancy, color_ids)` arrays."""
    width, height, depth = _validate_size(size)
    occupancy = np.ones((width, height, depth), dtype=bool)
    color_ids = np.full((width, height, depth), int(color_id), dtype=np.int32)
    return occupancy, color_ids


def make_stairs(
    width: int,
    steps: int,
    depth: int,
    color_id: int = 16,
) -> tuple[np.ndarray, np.ndarray]:
    """Create a simple staircase where each higher step occupies one less X column."""
    if width <= 0 or steps <= 0 or depth <= 0:
        raise ValueError("Width, steps, and depth must be positive.")
    occupancy = np.zeros((width, steps, depth), dtype=bool)
    for y in range(steps):
        occupied_width = max(width - y, 1)
        occupancy[:occupied_width, y, :] = True
    color_ids = np.full(occupancy.shape, int(color_id), dtype=np.int32)
    return occupancy, color_ids

