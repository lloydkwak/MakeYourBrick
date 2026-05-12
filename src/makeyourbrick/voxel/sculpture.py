from __future__ import annotations

from typing import Literal

import numpy as np

SCULPTURE_MODES = ("solid", "shell", "contour-shell", "density")
SculptureMode = Literal["solid", "shell", "contour-shell", "density"]
VOXEL_SMOOTHING_PRESETS = ("none", "light", "contour", "studio", "profile", "polished")
VoxelSmoothing = Literal["none", "light", "contour", "studio", "profile", "polished"]
INFILL_PATTERNS = ("lattice", "ribs")
InfillPattern = Literal["lattice", "ribs"]


def validate_sculpture_options(
    mode: str,
    wall_thickness: int,
    base_thickness: int,
    voxel_smoothing: str = "none",
    infill_density: float = 0.35,
    infill_pattern: str = "lattice",
) -> None:
    if mode not in SCULPTURE_MODES:
        raise ValueError(f"Unsupported sculpture mode: {mode}")
    if wall_thickness < 1:
        raise ValueError("wall_thickness must be at least 1.")
    if base_thickness < 0:
        raise ValueError("base_thickness must be non-negative.")
    if voxel_smoothing not in VOXEL_SMOOTHING_PRESETS:
        raise ValueError(f"Unsupported voxel smoothing preset: {voxel_smoothing}")
    if not 0.0 <= infill_density <= 1.0:
        raise ValueError("infill_density must be between 0.0 and 1.0.")
    if infill_pattern not in INFILL_PATTERNS:
        raise ValueError(f"Unsupported infill pattern: {infill_pattern}")


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


def horizontal_neighbor_count(mask: np.ndarray) -> np.ndarray:
    if mask.ndim != 3:
        raise ValueError("Mask must be a 3D array.")
    padded = np.pad(mask.astype(bool), 1, mode="constant", constant_values=False)
    counts = np.zeros(mask.shape, dtype=np.int16)
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        counts += padded[
            1 + dx : 1 + dx + mask.shape[0],
            1 : 1 + mask.shape[1],
            1 + dz : 1 + dz + mask.shape[2],
        ]
    return counts


def vertical_neighbor_count(mask: np.ndarray) -> np.ndarray:
    if mask.ndim != 3:
        raise ValueError("Mask must be a 3D array.")
    padded = np.pad(mask.astype(bool), 1, mode="constant", constant_values=False)
    counts = np.zeros(mask.shape, dtype=np.int16)
    for dy in (-1, 1):
        counts += padded[
            1 : 1 + mask.shape[0],
            1 + dy : 1 + dy + mask.shape[1],
            1 : 1 + mask.shape[2],
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


def remove_light_layer_spurs(occupancy: np.ndarray) -> np.ndarray:
    occupancy = occupancy.astype(bool)
    smoothed = occupancy.copy()
    horizontal_counts = horizontal_neighbor_count(occupancy)
    vertical_counts = vertical_neighbor_count(occupancy)
    spurs = occupancy & (horizontal_counts <= 1) & (vertical_counts == 0)
    smoothed[spurs] = False
    return smoothed


def apply_voxel_smoothing(occupancy: np.ndarray, preset: VoxelSmoothing = "none") -> np.ndarray:
    if preset not in VOXEL_SMOOTHING_PRESETS:
        raise ValueError(f"Unsupported voxel smoothing preset: {preset}")
    if preset == "none":
        return occupancy.astype(bool)
    if preset == "polished":
        return smooth_polished_layers(close_single_voxel_gaps(occupancy))
    if preset == "profile":
        return smooth_profile_layers(close_single_voxel_gaps(occupancy))
    if preset == "studio":
        return smooth_studio_layers(close_single_voxel_gaps(occupancy))
    smoothed = close_single_voxel_gaps(occupancy)
    smoothed = remove_light_layer_spurs(smoothed)
    if preset == "contour":
        smoothed = smooth_layer_contours(smoothed)
        smoothed = remove_light_layer_spurs(smoothed)
    return smoothed


def layer_neighbor_count(layer: np.ndarray) -> np.ndarray:
    if layer.ndim != 2:
        raise ValueError("Layer must be a 2D array.")
    padded = np.pad(layer.astype(bool), 1, mode="constant", constant_values=False)
    counts = np.zeros(layer.shape, dtype=np.int16)
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        counts += padded[
            1 + dx : 1 + dx + layer.shape[0],
            1 + dz : 1 + dz + layer.shape[1],
        ]
    return counts


def layer_neighbor_count_8(layer: np.ndarray) -> np.ndarray:
    if layer.ndim != 2:
        raise ValueError("Layer must be a 2D array.")
    padded = np.pad(layer.astype(bool), 1, mode="constant", constant_values=False)
    counts = np.zeros(layer.shape, dtype=np.int16)
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            if dx == 0 and dz == 0:
                continue
            counts += padded[
                1 + dx : 1 + dx + layer.shape[0],
                1 + dz : 1 + dz + layer.shape[1],
            ]
    return counts


def layer_surface_mask(layer: np.ndarray) -> np.ndarray:
    if layer.ndim != 2:
        raise ValueError("Layer must be a 2D array.")
    layer = layer.astype(bool)
    padded = np.pad(layer, 1, mode="constant", constant_values=False)
    interior = layer.copy()
    for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        interior &= padded[
            1 + dx : 1 + dx + layer.shape[0],
            1 + dz : 1 + dz + layer.shape[1],
        ]
    return layer & ~interior


def dilate_layer_within(layer_seed: np.ndarray, layer_limit: np.ndarray, iterations: int) -> np.ndarray:
    if layer_seed.ndim != 2 or layer_limit.ndim != 2:
        raise ValueError("Layer masks must be 2D arrays.")
    if layer_seed.shape != layer_limit.shape:
        raise ValueError("Layer masks must have the same shape.")
    result = layer_seed.astype(bool) & layer_limit.astype(bool)
    limit = layer_limit.astype(bool)
    for _ in range(max(0, iterations)):
        padded = np.pad(result, 1, mode="constant", constant_values=False)
        expanded = result.copy()
        expanded |= padded[:-2, 1:-1]
        expanded |= padded[2:, 1:-1]
        expanded |= padded[1:-1, :-2]
        expanded |= padded[1:-1, 2:]
        result = expanded & limit
    return result


def contour_shell_mask(occupancy: np.ndarray, wall_thickness: int) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    shell = np.zeros_like(occupancy, dtype=bool)
    for y in range(occupancy.shape[1]):
        layer = occupancy[:, y, :].astype(bool)
        if not layer.any():
            continue
        boundary = layer_surface_mask(layer)
        shell[:, y, :] = dilate_layer_within(boundary, layer, wall_thickness - 1)
    return shell


def add_vertical_support_columns(
    mask: np.ndarray,
    occupancy: np.ndarray,
    base_thickness: int = 0,
    support_spacing: int = 1,
) -> np.ndarray:
    if mask.ndim != 3 or occupancy.ndim != 3:
        raise ValueError("Masks must be 3D arrays.")
    if mask.shape != occupancy.shape:
        raise ValueError("Masks must have the same shape.")
    supported = mask.astype(bool).copy()
    limit = occupancy.astype(bool)
    start_y = max(1, int(base_thickness))
    spacing = max(1, int(support_spacing))
    for y in range(start_y, supported.shape[1]):
        unsupported = supported[:, y, :] & ~supported[:, y - 1, :]
        for x, z in np.argwhere(unsupported):
            if spacing > 1 and ((int(x) + int(z) + y) % spacing) != 0:
                continue
            supported[int(x), :y, int(z)] |= limit[int(x), :y, int(z)]
    return supported & limit


def layer_components(layer: np.ndarray) -> list[list[tuple[int, int]]]:
    if layer.ndim != 2:
        raise ValueError("Layer must be a 2D array.")
    layer = layer.astype(bool)
    visited = np.zeros_like(layer, dtype=bool)
    components: list[list[tuple[int, int]]] = []
    width, depth = layer.shape
    for start in np.argwhere(layer):
        x, z = (int(value) for value in start)
        if visited[x, z]:
            continue
        stack = [(x, z)]
        visited[x, z] = True
        component: list[tuple[int, int]] = []
        while stack:
            cx, cz = stack.pop()
            component.append((cx, cz))
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, nz = cx + dx, cz + dz
                if not (0 <= nx < width and 0 <= nz < depth):
                    continue
                if layer[nx, nz] and not visited[nx, nz]:
                    visited[nx, nz] = True
                    stack.append((nx, nz))
        components.append(component)
    return components


def remove_small_layer_components(
    layer: np.ndarray,
    *,
    min_size: int = 4,
    min_largest_ratio: float = 0.03,
) -> np.ndarray:
    if layer.ndim != 2:
        raise ValueError("Layer must be a 2D array.")
    layer = layer.astype(bool)
    components = layer_components(layer)
    if len(components) <= 1:
        return layer.copy()
    largest_size = max(len(component) for component in components)
    threshold = max(int(min_size), int(np.ceil(largest_size * float(min_largest_ratio))))
    retained = np.zeros_like(layer, dtype=bool)
    for component in components:
        if len(component) >= threshold:
            for x, z in component:
                retained[x, z] = True
    return retained


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


def smooth_2d_contour(layer: np.ndarray) -> np.ndarray:
    layer = fill_2d_holes(layer)
    counts = layer_neighbor_count(layer)
    smoothed = layer.copy()
    smoothed[(~layer) & (counts >= 3)] = True
    smoothed[layer & (counts <= 1)] = False
    return smoothed


def smooth_2d_polished_contour(layer: np.ndarray) -> np.ndarray:
    if layer.ndim != 2:
        raise ValueError("Layer must be a 2D array.")
    layer = fill_2d_holes(layer)
    counts4 = layer_neighbor_count(layer)
    counts8 = layer_neighbor_count_8(layer)
    smoothed = layer.copy()
    smoothed[(~layer) & ((counts4 >= 3) | (counts8 >= 5))] = True
    smoothed[layer & ((counts4 <= 1) | (counts8 <= 2))] = False
    smoothed = fill_2d_holes(smoothed)
    return remove_small_layer_components(smoothed, min_size=6, min_largest_ratio=0.04)


def smooth_layer_contours(occupancy: np.ndarray) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    smoothed = occupancy.astype(bool).copy()
    for y in range(smoothed.shape[1]):
        smoothed[:, y, :] = smooth_2d_contour(smoothed[:, y, :])
    return smoothed


def fill_vertical_layer_gaps(occupancy: np.ndarray) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    filled = occupancy.astype(bool).copy()
    if filled.shape[1] < 3:
        return filled
    above = filled[:, :-2, :]
    current = filled[:, 1:-1, :]
    below = filled[:, 2:, :]
    current[(~current) & above & below] = True
    filled[:, 1:-1, :] = current
    return filled


def smooth_studio_layers(occupancy: np.ndarray, iterations: int = 2) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    smoothed = occupancy.astype(bool).copy()
    for _ in range(max(1, iterations)):
        smoothed = fill_vertical_layer_gaps(smoothed)
        for y in range(smoothed.shape[1]):
            layer = fill_2d_holes(smoothed[:, y, :])
            counts = layer_neighbor_count(layer)
            layer[(~layer) & (counts >= 3)] = True
            smoothed[:, y, :] = layer
        smoothed = fill_vertical_layer_gaps(smoothed)
        smoothed = remove_light_layer_spurs(smoothed)
    return smoothed


def trim_layer_to_neighbor_profile(
    layer: np.ndarray,
    neighbor_profile: np.ndarray,
    *,
    max_extra_neighbor_distance: int = 1,
) -> np.ndarray:
    if layer.ndim != 2 or neighbor_profile.ndim != 2:
        raise ValueError("Layer masks must be 2D arrays.")
    if layer.shape != neighbor_profile.shape:
        raise ValueError("Layer masks must have the same shape.")
    layer = layer.astype(bool)
    profile = neighbor_profile.astype(bool)
    if not layer.any() or not profile.any():
        return layer.copy()
    expanded = profile.copy()
    for _ in range(max(0, max_extra_neighbor_distance)):
        padded = np.pad(expanded, 1, mode="constant", constant_values=False)
        expanded |= padded[:-2, 1:-1]
        expanded |= padded[2:, 1:-1]
        expanded |= padded[1:-1, :-2]
        expanded |= padded[1:-1, 2:]
    return layer & expanded


def smooth_profile_layers(occupancy: np.ndarray, iterations: int = 2) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    smoothed = smooth_studio_layers(occupancy, iterations=1)
    for _ in range(max(1, iterations)):
        smoothed = fill_vertical_layer_gaps(smoothed)
        for y in range(smoothed.shape[1]):
            layer = fill_2d_holes(smoothed[:, y, :])
            layer = smooth_2d_contour(layer)
            layer = remove_small_layer_components(layer)
            smoothed[:, y, :] = layer
        if smoothed.shape[1] >= 3:
            previous_layers = smoothed[:, :-2, :]
            current_layers = smoothed[:, 1:-1, :]
            next_layers = smoothed[:, 2:, :]
            for y in range(1, smoothed.shape[1] - 1):
                neighbor_profile = previous_layers[:, y - 1, :] | next_layers[:, y - 1, :]
                current_layers[:, y - 1, :] = trim_layer_to_neighbor_profile(
                    current_layers[:, y - 1, :],
                    neighbor_profile,
                    max_extra_neighbor_distance=1,
                )
            smoothed[:, 1:-1, :] = current_layers
        smoothed = fill_vertical_layer_gaps(smoothed)
        smoothed = remove_light_layer_spurs(smoothed)
    return smoothed


def smooth_polished_layers(occupancy: np.ndarray, iterations: int = 3) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    smoothed = smooth_profile_layers(occupancy, iterations=1)
    for _ in range(max(1, iterations)):
        smoothed = fill_vertical_layer_gaps(smoothed)
        for y in range(smoothed.shape[1]):
            smoothed[:, y, :] = smooth_2d_polished_contour(smoothed[:, y, :])
        if smoothed.shape[1] >= 3:
            for y in range(1, smoothed.shape[1] - 1):
                neighbor_profile = smoothed[:, y - 1, :] | smoothed[:, y + 1, :]
                smoothed[:, y, :] = trim_layer_to_neighbor_profile(
                    smoothed[:, y, :],
                    neighbor_profile,
                    max_extra_neighbor_distance=1,
                )
        smoothed = fill_vertical_layer_gaps(smoothed)
        smoothed = remove_light_layer_spurs(smoothed)
    return smoothed


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


def lattice_spacing_for_density(density: float) -> int:
    if not 0.0 <= density <= 1.0:
        raise ValueError("density must be between 0.0 and 1.0.")
    if density <= 0.0:
        return 0
    if density >= 1.0:
        return 1
    best_spacing = 2
    best_error = float("inf")
    for spacing in range(2, 33):
        ratio = (2.0 / spacing) - (1.0 / (spacing * spacing))
        error = abs(ratio - density)
        if error < best_error:
            best_spacing = spacing
            best_error = error
    return best_spacing


def lattice_infill_mask(occupancy: np.ndarray, density: float) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    spacing = lattice_spacing_for_density(density)
    if spacing == 0:
        return np.zeros_like(occupancy, dtype=bool)
    if spacing == 1:
        return occupancy.astype(bool)
    x_indices, _y_indices, z_indices = np.indices(occupancy.shape)
    lattice = ((x_indices % spacing) == 0) | ((z_indices % spacing) == 0)
    return occupancy.astype(bool) & lattice


def rib_infill_mask(occupancy: np.ndarray, density: float) -> np.ndarray:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    spacing = lattice_spacing_for_density(density)
    if spacing == 0:
        return np.zeros_like(occupancy, dtype=bool)
    if spacing == 1:
        return occupancy.astype(bool)
    x_indices, y_indices, z_indices = np.indices(occupancy.shape)
    x_ribs = (x_indices % spacing) == (y_indices % spacing)
    z_ribs = (z_indices % spacing) == ((y_indices + spacing // 2) % spacing)
    vertical_posts = ((x_indices % spacing) == 0) & ((z_indices % spacing) == 0)
    return occupancy.astype(bool) & (x_ribs | z_ribs | vertical_posts)


def infill_mask(occupancy: np.ndarray, density: float, pattern: InfillPattern = "lattice") -> np.ndarray:
    if pattern == "lattice":
        return lattice_infill_mask(occupancy, density)
    if pattern == "ribs":
        return rib_infill_mask(occupancy, density)
    raise ValueError(f"Unsupported infill pattern: {pattern}")


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
    voxel_smoothing: VoxelSmoothing = "none",
    infill_density: float = 0.35,
    infill_pattern: InfillPattern = "lattice",
) -> tuple[np.ndarray, np.ndarray]:
    validate_sculpture_options(
        mode,
        wall_thickness,
        base_thickness,
        voxel_smoothing,
        infill_density,
        infill_pattern,
    )
    if color_ids.shape != occupancy.shape:
        raise ValueError("Color id array must have the same shape as occupancy.")
    occupancy = occupancy.astype(bool)
    solid_occupancy = apply_voxel_smoothing(preprocess_solid_occupancy(occupancy), voxel_smoothing)
    if mode == "solid":
        return solid_occupancy, repair_sculpture_colors(occupancy, solid_occupancy, color_ids)

    shell_occupancy = solid_occupancy
    if mode == "contour-shell":
        shell = contour_shell_mask(shell_occupancy, wall_thickness)
    else:
        shell = dilate_within_occupancy(surface_mask(shell_occupancy), shell_occupancy, wall_thickness - 1)
    retained = shell | base_fill_mask(shell_occupancy, base_thickness)
    if mode == "density":
        interior = shell_occupancy & ~retained
        retained |= infill_mask(interior, infill_density, infill_pattern)
    retained = anchor_shell_to_base(retained, shell_occupancy, base_thickness)
    if mode == "contour-shell":
        retained = add_vertical_support_columns(retained, shell_occupancy, base_thickness, support_spacing=3)
    return retained, repair_sculpture_colors(occupancy, retained, color_ids)
