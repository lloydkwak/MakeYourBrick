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


def neighbor_count(mask: np.ndarray) -> np.ndarray:
    if mask.ndim != 3:
        raise ValueError("Mask must be a 3D array.")
    padded = np.pad(mask.astype(bool), 1, mode="constant", constant_values=False)
    counts = np.zeros(mask.shape, dtype=np.int16)
    for dx, dy, dz in (
        (-1, 0, 0),
        (1, 0, 0),
        (0, -1, 0),
        (0, 1, 0),
        (0, 0, -1),
        (0, 0, 1),
    ):
        counts += padded[
            1 + dx : 1 + dx + mask.shape[0],
            1 + dy : 1 + dy + mask.shape[1],
            1 + dz : 1 + dz + mask.shape[2],
        ]
    return counts


def close_single_voxel_gaps(occupancy: np.ndarray) -> np.ndarray:
    occupancy = occupancy.astype(bool)
    closed = occupancy.copy()
    closed[(~occupancy) & (neighbor_count(occupancy) >= 5)] = True
    return closed


def remove_isolated_features(occupancy: np.ndarray) -> np.ndarray:
    occupancy = occupancy.astype(bool)
    opened = occupancy.copy()
    opened[occupancy & (neighbor_count(occupancy) == 0)] = False
    return opened


def fill_2d_holes(layer: np.ndarray) -> np.ndarray:
    if layer.ndim != 2:
        raise ValueError("Layer must be a 2D array.")
    layer = layer.astype(bool)
    outside = np.zeros_like(layer, dtype=bool)
    stack: list[tuple[int, int]] = []
    width, depth = layer.shape
    for x in range(width):
        for z in (0, depth - 1):
            if not layer[x, z] and not outside[x, z]:
                outside[x, z] = True
                stack.append((x, z))
    for z in range(depth):
        for x in (0, width - 1):
            if not layer[x, z] and not outside[x, z]:
                outside[x, z] = True
                stack.append((x, z))
    while stack:
        cx, cz = stack.pop()
        for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, nz = cx + dx, cz + dz
            if not (0 <= nx < width and 0 <= nz < depth):
                continue
            if not layer[nx, nz] and not outside[nx, nz]:
                outside[nx, nz] = True
                stack.append((nx, nz))
    return layer | (~layer & ~outside)


def fill_horizontal_layer_holes(occupancy: np.ndarray) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    filled = occupancy.astype(bool).copy()
    for y in range(filled.shape[1]):
        filled[:, y, :] = fill_2d_holes(filled[:, y, :])
    return filled


def preprocess_solid_occupancy(occupancy: np.ndarray) -> np.ndarray:
    closed = close_single_voxel_gaps(occupancy)
    filled = fill_horizontal_layer_holes(closed)
    return remove_isolated_features(filled)


def preprocess_shell_occupancy(occupancy: np.ndarray) -> np.ndarray:
    return preprocess_solid_occupancy(occupancy)


def repair_sculpture_colors(
    original_occupancy: np.ndarray,
    repaired_occupancy: np.ndarray,
    color_ids: np.ndarray,
    default_color_id: int = 16,
) -> np.ndarray:
    repaired_colors = color_ids.copy()
    new_voxels = repaired_occupancy & ~original_occupancy
    for y in range(repaired_occupancy.shape[1]):
        layer_new = new_voxels[:, y, :]
        if not layer_new.any():
            continue
        layer_existing = original_occupancy[:, y, :]
        layer_color_values = color_ids[:, y, :][layer_existing]
        if len(layer_color_values):
            values, counts = np.unique(layer_color_values, return_counts=True)
            fill_color = int(values[int(np.argmax(counts))])
        else:
            fill_color = int(default_color_id)
        repaired_colors[:, y, :][layer_new] = fill_color
    repaired_colors[~repaired_occupancy] = 0
    return repaired_colors




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


def connected_components(mask: np.ndarray) -> list[list[tuple[int, int, int]]]:
    if mask.ndim != 3:
        raise ValueError("Mask must be a 3D array.")
    visited = np.zeros_like(mask, dtype=bool)
    components: list[list[tuple[int, int, int]]] = []
    width, height, depth = mask.shape
    for start in np.argwhere(mask):
        x, y, z = (int(value) for value in start)
        if visited[x, y, z]:
            continue
        stack = [(x, y, z)]
        visited[x, y, z] = True
        component: list[tuple[int, int, int]] = []
        while stack:
            cx, cy, cz = stack.pop()
            component.append((cx, cy, cz))
            for dx, dy, dz in (
                (-1, 0, 0),
                (1, 0, 0),
                (0, -1, 0),
                (0, 1, 0),
                (0, 0, -1),
                (0, 0, 1),
            ):
                nx, ny, nz = cx + dx, cy + dy, cz + dz
                if not (0 <= nx < width and 0 <= ny < height and 0 <= nz < depth):
                    continue
                if mask[nx, ny, nz] and not visited[nx, ny, nz]:
                    visited[nx, ny, nz] = True
                    stack.append((nx, ny, nz))
        components.append(component)
    return components


def anchor_shell_to_base(shell: np.ndarray, occupancy: np.ndarray, base_thickness: int) -> np.ndarray:
    if base_thickness <= 0:
        return shell
    anchored = shell.copy()
    for component in connected_components(shell):
        if any(y < base_thickness for _x, y, _z in component):
            continue
        anchor_x, anchor_y, anchor_z = min(component, key=lambda item: item[1])
        anchored[anchor_x, : anchor_y + 1, anchor_z] |= occupancy[anchor_x, : anchor_y + 1, anchor_z]
    return anchored


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
    solid_occupancy = preprocess_solid_occupancy(occupancy)
    if mode == "solid":
        return solid_occupancy, repair_sculpture_colors(occupancy, solid_occupancy, color_ids)

    shell_occupancy = solid_occupancy
    shell = dilate_within_occupancy(surface_mask(shell_occupancy), shell_occupancy, wall_thickness - 1)
    retained = shell | base_fill_mask(shell_occupancy, base_thickness)
    retained = anchor_shell_to_base(retained, shell_occupancy, base_thickness)
    retained_colors = color_ids.copy()
    retained_colors[~retained] = 0
    return retained, retained_colors
