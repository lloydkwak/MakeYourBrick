from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import trimesh
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps are absent.
    trimesh = None

from makeyourbrick.brickify.colors import quantize_voxel_rgb_to_ldraw
from makeyourbrick.mesh.color_sampling import sample_mesh_rgb
from makeyourbrick.types import VoxelArtifact

VOXELIZERS = ("surface", "ray", "slice", "slice-surface")
RAY_FILL_MODES = ("wide", "balanced")


def compute_pitch(mesh, target_longest_studs: int, min_pitch: float = 0.005) -> float:
    if target_longest_studs <= 0:
        raise ValueError("target_longest_studs must be positive.")
    longest = float(mesh.extents.max())
    if longest <= 0:
        raise ValueError("Mesh has zero-sized bounds.")
    return max(longest / target_longest_studs, min_pitch)


def compute_footprint_pitch(mesh, base_size_studs: int, min_pitch: float = 0.005) -> float:
    if base_size_studs <= 0:
        raise ValueError("base_size_studs must be positive.")
    footprint = float(max(mesh.extents[0], mesh.extents[2]))
    if footprint <= 0:
        raise ValueError("Mesh has zero-sized X/Z footprint.")
    return max(footprint / base_size_studs, min_pitch)


def save_voxel_artifact(
    output_path: Path,
    occupancy: np.ndarray,
    color_ids: np.ndarray,
    rgb: np.ndarray,
    origin: np.ndarray,
    pitch: float,
) -> VoxelArtifact:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    if color_ids.shape != occupancy.shape:
        raise ValueError("Color id array must have the same shape as occupancy.")
    if rgb.shape != (*occupancy.shape, 3):
        raise ValueError("RGB array must have shape occupancy.shape + (3,).")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        occupancy=occupancy.astype(bool),
        color_ids=color_ids.astype(np.int32),
        rgb=rgb.astype(np.uint8),
        origin=np.asarray(origin, dtype=np.float32),
        pitch=np.float32(pitch),
    )
    return VoxelArtifact(
        path=output_path,
        pitch=float(pitch),
        origin=tuple(float(v) for v in np.asarray(origin, dtype=np.float32)),
    )


def load_voxel_artifact(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    with np.load(path) as data:
        occupancy = data["occupancy"].astype(bool)
        color_ids = data["color_ids"].astype(np.int32)
        rgb = data["rgb"].astype(np.uint8)
        origin = data["origin"].astype(np.float32)
        pitch = float(data["pitch"])
    return occupancy, color_ids, rgb, origin, pitch


def voxel_grid_origin(grid) -> np.ndarray:
    if hasattr(grid, "origin"):
        return np.asarray(grid.origin, dtype=np.float32)
    if hasattr(grid, "transform"):
        return np.asarray(grid.transform[:3, 3], dtype=np.float32)
    return np.zeros(3, dtype=np.float32)


def occupied_indices_to_points(grid, occupancy: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    indices = np.argwhere(occupancy)
    if len(indices) == 0:
        return indices, np.zeros((0, 3), dtype=np.float32)
    if hasattr(grid, "indices_to_points"):
        points = np.asarray(grid.indices_to_points(indices), dtype=np.float32)
    else:
        transform = np.asarray(grid.transform, dtype=np.float32)
        homogenous = np.column_stack([indices, np.ones(len(indices), dtype=np.float32)])
        points = (transform @ homogenous.T).T[:, :3]
    return indices, points


def occupied_indices_to_center_points(
    occupancy: np.ndarray,
    origin: np.ndarray,
    pitch: float,
) -> tuple[np.ndarray, np.ndarray]:
    indices = np.argwhere(occupancy)
    if len(indices) == 0:
        return indices, np.zeros((0, 3), dtype=np.float32)
    points = np.asarray(origin, dtype=np.float32) + (indices.astype(np.float32) + 0.5) * float(pitch)
    return indices, points


def voxelize_mesh_with_surface(mesh, pitch: float, fill: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    grid = mesh.voxelized(pitch)
    if fill:
        grid = grid.fill()
    occupancy = grid.matrix.astype(bool)
    indices, points = occupied_indices_to_points(grid, occupancy)
    return occupancy, voxel_grid_origin(grid), points_for_indices(occupancy, indices, points)


def points_for_indices(occupancy: np.ndarray, indices: np.ndarray, points: np.ndarray) -> np.ndarray:
    point_grid = np.zeros((*occupancy.shape, 3), dtype=np.float32)
    if len(indices):
        point_grid[indices[:, 0], indices[:, 1], indices[:, 2]] = points
    return point_grid


def _dedupe_sorted_hits(values: np.ndarray, tolerance: float) -> list[float]:
    if len(values) == 0:
        return []
    sorted_values = sorted(float(value) for value in values)
    deduped = [sorted_values[0]]
    for value in sorted_values[1:]:
        if abs(value - deduped[-1]) > tolerance:
            deduped.append(value)
    return deduped


def _pair_ray_hit_intervals(hits: list[float], mode: str = "wide") -> list[tuple[float, float]]:
    if mode not in RAY_FILL_MODES:
        raise ValueError(f"Unsupported ray fill mode: {mode}")
    if len(hits) < 2:
        return []
    if len(hits) % 2 == 0:
        return list(zip(hits[0::2], hits[1::2]))
    if mode == "wide":
        return [(hits[0], hits[-1])]

    best_intervals: list[tuple[float, float]] = []
    best_length: float | None = None
    for drop_index in range(len(hits)):
        candidate_hits = hits[:drop_index] + hits[drop_index + 1 :]
        intervals = list(zip(candidate_hits[0::2], candidate_hits[1::2]))
        interval_length = sum(abs(end - start) for start, end in intervals)
        if best_length is None or interval_length < best_length:
            best_length = interval_length
            best_intervals = intervals
    return best_intervals


def voxelize_mesh_with_vertical_rays(
    mesh,
    pitch: float,
    ray_fill: str = "wide",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if ray_fill not in RAY_FILL_MODES:
        raise ValueError(f"Unsupported ray fill mode: {ray_fill}")
    bounds = np.asarray(mesh.bounds, dtype=np.float64)
    extents = np.asarray(mesh.extents, dtype=np.float64)
    shape = np.maximum(1, np.ceil(extents / pitch).astype(int))
    origin = bounds[0].astype(np.float32)
    x_centers = bounds[0, 0] + (np.arange(shape[0], dtype=np.float64) + 0.5) * pitch
    y_centers = bounds[0, 1] + (np.arange(shape[1], dtype=np.float64) + 0.5) * pitch
    z_centers = bounds[0, 2] + (np.arange(shape[2], dtype=np.float64) + 0.5) * pitch
    origins = np.array(
        [[x, bounds[0, 1] - pitch, z] for x in x_centers for z in z_centers],
        dtype=np.float64,
    )
    directions = np.tile(np.array([[0.0, 1.0, 0.0]], dtype=np.float64), (len(origins), 1))
    locations, ray_indices, _triangle_indices = mesh.ray.intersects_location(
        origins,
        directions,
        multiple_hits=True,
    )
    occupancy = np.zeros(tuple(int(value) for value in shape), dtype=bool)
    hits_by_ray: dict[int, list[float]] = {}
    for location, ray_index in zip(locations, ray_indices):
        hits_by_ray.setdefault(int(ray_index), []).append(float(location[1]))
    ray_count_z = shape[2]
    tolerance = max(float(pitch) * 0.1, 1e-8)
    for ray_index, hit_values in hits_by_ray.items():
        hits = _dedupe_sorted_hits(np.asarray(hit_values, dtype=np.float64), tolerance=tolerance)
        intervals = _pair_ray_hit_intervals(hits, mode=ray_fill)
        x_index = ray_index // ray_count_z
        z_index = ray_index % ray_count_z
        for start, end in intervals:
            if end < start:
                start, end = end, start
            occupancy[x_index, (y_centers >= start) & (y_centers <= end), z_index] = True
    indices, points = occupied_indices_to_center_points(occupancy, origin, pitch)
    return occupancy, origin, points_for_indices(occupancy, indices, points)


def _points_on_polyline_boundary(
    points: np.ndarray,
    polyline: np.ndarray,
    tolerance: float,
) -> np.ndarray:
    if len(polyline) < 2:
        return np.zeros(len(points), dtype=bool)
    on_boundary = np.zeros(len(points), dtype=bool)
    for start, end in zip(polyline[:-1], polyline[1:]):
        segment = end - start
        length_sq = float(np.dot(segment, segment))
        if length_sq <= 1e-18:
            continue
        relative = points - start
        projection = np.clip((relative @ segment) / length_sq, 0.0, 1.0)
        closest = start + projection[:, None] * segment
        distance = np.linalg.norm(points - closest, axis=1)
        on_boundary |= distance <= tolerance
    return on_boundary


def _points_inside_polyline(points: np.ndarray, polyline: np.ndarray, tolerance: float) -> np.ndarray:
    if len(polyline) < 3:
        return np.zeros(len(points), dtype=bool)
    if not np.allclose(polyline[0], polyline[-1]):
        polyline = np.vstack([polyline, polyline[0]])
    on_boundary = _points_on_polyline_boundary(points, polyline, tolerance)
    x = points[:, 0]
    z = points[:, 1]
    inside = np.zeros(len(points), dtype=bool)
    x0 = polyline[:-1, 0]
    z0 = polyline[:-1, 1]
    x1 = polyline[1:, 0]
    z1 = polyline[1:, 1]
    for edge_x0, edge_z0, edge_x1, edge_z1 in zip(x0, z0, x1, z1):
        crosses = (edge_z0 > z) != (edge_z1 > z)
        x_intersections = (edge_x1 - edge_x0) * (z - edge_z0) / (edge_z1 - edge_z0 + 1e-18) + edge_x0
        inside ^= crosses & (x < x_intersections)
    return inside | on_boundary


def _points_inside_contours(
    points: np.ndarray,
    contours: list[np.ndarray],
    tolerance: float,
    fill_rule: str = "xor",
) -> np.ndarray:
    if fill_rule not in {"xor", "union"}:
        raise ValueError(f"Unsupported contour fill rule: {fill_rule}")
    inside = np.zeros(len(points), dtype=bool)
    for contour in contours:
        contour_inside = _points_inside_polyline(points, contour, tolerance)
        if fill_rule == "union":
            inside |= contour_inside
        else:
            inside ^= contour_inside
    return inside


def _points_near_contours(points: np.ndarray, contours: list[np.ndarray], tolerance: float) -> np.ndarray:
    near = np.zeros(len(points), dtype=bool)
    for contour in contours:
        near |= _points_on_polyline_boundary(points, contour, tolerance)
    return near


def voxelize_mesh_with_layer_slices(
    mesh,
    pitch: float,
    contour_fill_rule: str = "union",
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    bounds = np.asarray(mesh.bounds, dtype=np.float64)
    extents = np.asarray(mesh.extents, dtype=np.float64)
    shape = np.maximum(1, np.ceil(extents / pitch).astype(int))
    origin = bounds[0].astype(np.float32)
    x_centers = bounds[0, 0] + (np.arange(shape[0], dtype=np.float64) + 0.5) * pitch
    y_centers = bounds[0, 1] + (np.arange(shape[1], dtype=np.float64) + 0.5) * pitch
    z_centers = bounds[0, 2] + (np.arange(shape[2], dtype=np.float64) + 0.5) * pitch
    grid_x, grid_z = np.meshgrid(x_centers, z_centers, indexing="ij")
    layer_points = np.column_stack([grid_x.ravel(), grid_z.ravel()])
    occupancy = np.zeros(tuple(int(value) for value in shape), dtype=bool)
    tolerance = max(float(pitch) * 0.05, 1e-8)
    for y_index, y_value in enumerate(y_centers):
        section = mesh.section(
            plane_origin=[0.0, float(y_value), 0.0],
            plane_normal=[0.0, 1.0, 0.0],
        )
        if section is None:
            continue
        contours = [
            np.asarray(path[:, [0, 2]], dtype=np.float64)
            for path in section.discrete
            if len(path) >= 3
        ]
        if not contours:
            continue
        inside = _points_inside_contours(
            layer_points,
            contours,
            tolerance=tolerance,
            fill_rule=contour_fill_rule,
        )
        occupancy[:, y_index, :] = inside.reshape(shape[0], shape[2])
    indices, points = occupied_indices_to_center_points(occupancy, origin, pitch)
    return occupancy, origin, points_for_indices(occupancy, indices, points)


def voxelize_mesh_with_surface_layer_slices(
    mesh,
    pitch: float,
    contour_tolerance_ratio: float = 0.55,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    bounds = np.asarray(mesh.bounds, dtype=np.float64)
    extents = np.asarray(mesh.extents, dtype=np.float64)
    shape = np.maximum(1, np.ceil(extents / pitch).astype(int))
    origin = bounds[0].astype(np.float32)
    x_centers = bounds[0, 0] + (np.arange(shape[0], dtype=np.float64) + 0.5) * pitch
    y_centers = bounds[0, 1] + (np.arange(shape[1], dtype=np.float64) + 0.5) * pitch
    z_centers = bounds[0, 2] + (np.arange(shape[2], dtype=np.float64) + 0.5) * pitch
    grid_x, grid_z = np.meshgrid(x_centers, z_centers, indexing="ij")
    layer_points = np.column_stack([grid_x.ravel(), grid_z.ravel()])
    occupancy = np.zeros(tuple(int(value) for value in shape), dtype=bool)
    tolerance = max(float(pitch) * float(contour_tolerance_ratio), 1e-8)
    for y_index, y_value in enumerate(y_centers):
        section = mesh.section(
            plane_origin=[0.0, float(y_value), 0.0],
            plane_normal=[0.0, 1.0, 0.0],
        )
        if section is None:
            continue
        contours = [
            np.asarray(path[:, [0, 2]], dtype=np.float64)
            for path in section.discrete
            if len(path) >= 2
        ]
        if not contours:
            continue
        near = _points_near_contours(layer_points, contours, tolerance=tolerance)
        occupancy[:, y_index, :] = near.reshape(shape[0], shape[2])
    indices, points = occupied_indices_to_center_points(occupancy, origin, pitch)
    return occupancy, origin, points_for_indices(occupancy, indices, points)


def voxelize_mesh(
    mesh,
    output_path: Path,
    pitch: float,
    fill: bool = True,
    default_color_id: int = 16,
    default_rgb: tuple[int, int, int] | None = None,
    palette_ids: np.ndarray | None = None,
    palette_rgb: np.ndarray | None = None,
    sample_colors: bool = False,
    voxelizer: str = "surface",
    ray_fill: str = "wide",
) -> VoxelArtifact:
    if voxelizer not in VOXELIZERS:
        raise ValueError(f"Unsupported voxelizer: {voxelizer}")
    if voxelizer == "ray":
        occupancy, origin, point_grid = voxelize_mesh_with_vertical_rays(mesh, pitch, ray_fill=ray_fill)
    elif voxelizer == "slice":
        occupancy, origin, point_grid = voxelize_mesh_with_layer_slices(mesh, pitch)
    elif voxelizer == "slice-surface":
        occupancy, origin, point_grid = voxelize_mesh_with_surface_layer_slices(mesh, pitch)
    else:
        occupancy, origin, point_grid = voxelize_mesh_with_surface(mesh, pitch, fill=fill)
    rgb = np.zeros((*occupancy.shape, 3), dtype=np.uint8)
    rgb_value = default_rgb or (160, 165, 169)
    if sample_colors:
        indices = np.argwhere(occupancy)
        points = point_grid[occupancy]
        rgb_values = sample_mesh_rgb(mesh, points, default_rgb=rgb_value)
        if len(indices):
            rgb[indices[:, 0], indices[:, 1], indices[:, 2]] = rgb_values
    else:
        rgb[occupancy] = rgb_value
    if palette_ids is not None or palette_rgb is not None:
        if palette_ids is None or palette_rgb is None:
            raise ValueError("Both palette_ids and palette_rgb are required for RGB quantization.")
        color_ids = quantize_voxel_rgb_to_ldraw(
            occupancy,
            rgb,
            palette_ids,
            palette_rgb,
            default_color_id=default_color_id,
        )
    else:
        color_ids = np.full(occupancy.shape, int(default_color_id), dtype=np.int32)
    return save_voxel_artifact(output_path, occupancy, color_ids, rgb, origin, pitch)
