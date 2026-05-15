from __future__ import annotations

import numpy as np

VOXEL_SMOOTHING_PRESETS = ("polished",)


def neighbor_count(mask: np.ndarray) -> np.ndarray:
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
        counts += padded[1 + dx : 1 + dx + mask.shape[0], 1 + dy : 1 + dy + mask.shape[1], 1 + dz : 1 + dz + mask.shape[2]]
    return counts


def layer_neighbor_count(layer: np.ndarray) -> np.ndarray:
    padded = np.pad(layer.astype(bool), 1, mode="constant", constant_values=False)
    counts = np.zeros(layer.shape, dtype=np.int16)
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        counts += padded[1 + dx : 1 + dx + layer.shape[0], 1 + dz : 1 + dz + layer.shape[1]]
    return counts


def layer_neighbor_count_8(layer: np.ndarray) -> np.ndarray:
    padded = np.pad(layer.astype(bool), 1, mode="constant", constant_values=False)
    counts = np.zeros(layer.shape, dtype=np.int16)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            if dx == 0 and dz == 0:
                continue
            counts += padded[1 + dx : 1 + dx + layer.shape[0], 1 + dz : 1 + dz + layer.shape[1]]
    return counts


def fill_2d_holes(layer: np.ndarray) -> np.ndarray:
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
        x, z = stack.pop()
        for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, nz = x + dx, z + dz
            if 0 <= nx < width and 0 <= nz < depth and not layer[nx, nz] and not outside[nx, nz]:
                outside[nx, nz] = True
                stack.append((nx, nz))
    return layer | (~layer & ~outside)


def close_single_voxel_gaps(occupancy: np.ndarray) -> np.ndarray:
    occupancy = occupancy.astype(bool)
    closed = occupancy.copy()
    closed[(~occupancy) & (neighbor_count(occupancy) >= 5)] = True
    return closed


def remove_isolated_features(occupancy: np.ndarray) -> np.ndarray:
    occupancy = occupancy.astype(bool)
    cleaned = occupancy.copy()
    cleaned[occupancy & (neighbor_count(occupancy) <= 1)] = False
    return cleaned


def fill_horizontal_layer_holes(occupancy: np.ndarray) -> np.ndarray:
    filled = occupancy.astype(bool).copy()
    for y in range(filled.shape[1]):
        filled[:, y, :] = fill_2d_holes(filled[:, y, :])
    return filled


def fill_vertical_layer_gaps(occupancy: np.ndarray) -> np.ndarray:
    filled = occupancy.astype(bool).copy()
    if filled.shape[1] < 3:
        return filled
    middle = filled[:, 1:-1, :]
    middle[(~middle) & filled[:, :-2, :] & filled[:, 2:, :]] = True
    filled[:, 1:-1, :] = middle
    return filled


def remove_small_layer_components(
    layer: np.ndarray,
    *,
    min_size: int = 6,
    min_largest_ratio: float = 0.04,
) -> np.ndarray:
    layer = layer.astype(bool)
    visited = np.zeros_like(layer, dtype=bool)
    components: list[list[tuple[int, int]]] = []
    width, depth = layer.shape
    for start_x, start_z in np.argwhere(layer):
        start = (int(start_x), int(start_z))
        if visited[start]:
            continue
        stack = [start]
        visited[start] = True
        component: list[tuple[int, int]] = []
        while stack:
            x, z = stack.pop()
            component.append((x, z))
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, nz = x + dx, z + dz
                if 0 <= nx < width and 0 <= nz < depth and layer[nx, nz] and not visited[nx, nz]:
                    visited[nx, nz] = True
                    stack.append((nx, nz))
        components.append(component)
    if len(components) <= 1:
        return layer
    largest = max(len(component) for component in components)
    threshold = max(int(min_size), int(np.ceil(largest * min_largest_ratio)))
    retained = np.zeros_like(layer, dtype=bool)
    for component in components:
        if len(component) >= threshold:
            for x, z in component:
                retained[x, z] = True
    return retained


def smooth_2d_polished_contour(layer: np.ndarray) -> np.ndarray:
    layer = fill_2d_holes(layer)
    counts4 = layer_neighbor_count(layer)
    counts8 = layer_neighbor_count_8(layer)
    smoothed = layer.copy()
    smoothed[(~layer) & ((counts4 >= 3) | (counts8 >= 5))] = True
    smoothed[layer & ((counts4 <= 1) | (counts8 <= 2))] = False
    return remove_small_layer_components(fill_2d_holes(smoothed))


def smooth_polished_layers(occupancy: np.ndarray, iterations: int = 3) -> np.ndarray:
    smoothed = occupancy.astype(bool).copy()
    for _ in range(max(1, iterations)):
        smoothed = fill_vertical_layer_gaps(smoothed)
        for y in range(smoothed.shape[1]):
            smoothed[:, y, :] = smooth_2d_polished_contour(smoothed[:, y, :])
    return smoothed


def apply_voxel_smoothing(occupancy: np.ndarray, preset: str = "polished") -> np.ndarray:
    if preset != "polished":
        raise ValueError("Only polished smoothing is supported.")
    return smooth_polished_layers(close_single_voxel_gaps(occupancy))


def preprocess_solid_occupancy(occupancy: np.ndarray) -> np.ndarray:
    return remove_isolated_features(fill_horizontal_layer_holes(close_single_voxel_gaps(occupancy)))


def layer_surface_mask(layer: np.ndarray) -> np.ndarray:
    layer = layer.astype(bool)
    padded = np.pad(layer, 1, mode="constant", constant_values=False)
    interior = layer.copy()
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        interior &= padded[1 + dx : 1 + dx + layer.shape[0], 1 + dz : 1 + dz + layer.shape[1]]
    return layer & ~interior


def dilate_layer_within(seed: np.ndarray, limit: np.ndarray, iterations: int) -> np.ndarray:
    result = seed.astype(bool) & limit.astype(bool)
    limit = limit.astype(bool)
    for _ in range(max(0, iterations)):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        expanded = result | padded[:-2, 1:-1] | padded[2:, 1:-1] | padded[1:-1, :-2] | padded[1:-1, 2:]
        result = expanded & limit
    return result


def contour_shell_mask(occupancy: np.ndarray, wall_thickness: int) -> np.ndarray:
    shell = np.zeros_like(occupancy, dtype=bool)
    for y in range(occupancy.shape[1]):
        layer = occupancy[:, y, :].astype(bool)
        if layer.any():
            shell[:, y, :] = dilate_layer_within(layer_surface_mask(layer), layer, wall_thickness - 1)
    return shell


def erode_volume_26(occupancy: np.ndarray, iterations: int) -> np.ndarray:
    eroded = occupancy.astype(bool).copy()
    for _ in range(max(0, iterations)):
        padded = np.pad(eroded, 1, mode="constant", constant_values=False)
        retained = eroded.copy()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    retained &= padded[
                        1 + dx : 1 + dx + eroded.shape[0],
                        1 + dy : 1 + dy + eroded.shape[1],
                        1 + dz : 1 + dz + eroded.shape[2],
                    ]
        eroded = retained
    return eroded


def volume_shell_mask(occupancy: np.ndarray, wall_thickness: int) -> np.ndarray:
    occupancy = occupancy.astype(bool)
    if wall_thickness <= 0:
        return np.zeros_like(occupancy, dtype=bool)
    interior = erode_volume_26(occupancy, wall_thickness)
    return occupancy & ~interior


def base_fill_mask(occupancy: np.ndarray, base_thickness: int) -> np.ndarray:
    base = np.zeros_like(occupancy, dtype=bool)
    thickness = min(base_thickness, occupancy.shape[1])
    if thickness <= 0:
        return base
    footprint = occupancy[:, :thickness, :].any(axis=1)
    base[:, :thickness, :] = footprint[:, None, :]
    return base


def repair_sculpture_colors(
    original_occupancy: np.ndarray,
    repaired_occupancy: np.ndarray,
    color_ids: np.ndarray,
    default_color_id: int = 16,
) -> np.ndarray:
    repaired = color_ids.copy()
    repaired[~repaired_occupancy] = 0
    new_voxels = repaired_occupancy & ~original_occupancy
    repaired[new_voxels] = int(default_color_id)
    return repaired.astype(np.int32)
