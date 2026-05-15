from __future__ import annotations

from pathlib import Path

import numpy as np

from makeyourbrick.types import VoxelArtifact

VOXELIZERS = ("slice", "surface")
AUTO_BASE_SIZE_OPTIONS = (16, 24, 32, 48, 64)


def compute_footprint_pitch(mesh, base_size_studs: int, min_pitch: float = 0.005) -> float:
    if base_size_studs <= 0:
        raise ValueError("base_size_studs must be positive.")
    footprint = float(max(mesh.extents[0], mesh.extents[2]))
    if footprint <= 0:
        raise ValueError("Mesh has zero-sized X/Z footprint.")
    return max(footprint / base_size_studs, min_pitch)


def recommend_base_size_studs(mesh, *, max_base_size: int = 64) -> int:
    extents = np.asarray(mesh.extents, dtype=np.float64)
    footprint = float(max(extents[0], extents[2]))
    if footprint <= 0:
        raise ValueError("Mesh has zero-sized X/Z footprint.")
    thinness = footprint / max(float(extents[1]), 1e-9)
    complexity = float(len(getattr(mesh, "faces", []))) / 50000.0
    component_count = 1
    if not bool(getattr(mesh, "is_watertight", False)):
        try:
            component_count = len(mesh.split(only_watertight=False))
        except Exception:
            component_count = 2
    fragmentation = min(component_count / 250.0, 4.0)
    score = thinness + complexity + fragmentation
    if score >= 10.0:
        recommended = 64
    elif score >= 6.0:
        recommended = 48
    elif score >= 3.5:
        recommended = 32
    elif score >= 2.0:
        recommended = 24
    else:
        recommended = 16
    return min(recommended, max_base_size)


def save_voxel_artifact(
    output_path: Path,
    occupancy: np.ndarray,
    color_ids: np.ndarray,
    rgb: np.ndarray,
    origin: np.ndarray,
    pitch: float,
    voxelizer: str = "slice",
) -> VoxelArtifact:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        occupancy=occupancy.astype(bool),
        color_ids=color_ids.astype(np.int32),
        rgb=rgb.astype(np.uint8),
        origin=np.asarray(origin, dtype=np.float32),
        pitch=np.float32(pitch),
        voxelizer=np.asarray(voxelizer),
    )
    return VoxelArtifact(
        path=output_path,
        pitch=float(pitch),
        origin=tuple(float(v) for v in np.asarray(origin, dtype=np.float32)),
        voxelizer=voxelizer,
    )


def load_voxel_artifact(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    with np.load(path) as data:
        return (
            data["occupancy"].astype(bool),
            data["color_ids"].astype(np.int32),
            data["rgb"].astype(np.uint8),
            data["origin"].astype(np.float32),
            float(data["pitch"]),
        )


def _points_on_polyline_boundary(points: np.ndarray, polyline: np.ndarray, tolerance: float) -> np.ndarray:
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
        on_boundary |= np.linalg.norm(points - closest, axis=1) <= tolerance
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
        x_hits = (edge_x1 - edge_x0) * (z - edge_z0) / (edge_z1 - edge_z0 + 1e-18) + edge_x0
        inside ^= crosses & (x < x_hits)
    return inside | on_boundary


def _points_inside_contours(points: np.ndarray, contours: list[np.ndarray], tolerance: float) -> np.ndarray:
    inside = np.zeros(len(points), dtype=bool)
    for contour in contours:
        inside ^= _points_inside_polyline(points, contour, tolerance)
    return inside


def voxelize_mesh_with_layer_slices(mesh, pitch: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    bounds = np.asarray(mesh.bounds, dtype=np.float64)
    extents = np.asarray(mesh.extents, dtype=np.float64)
    shape = np.maximum(1, np.ceil(extents / pitch).astype(int))
    origin = bounds[0].astype(np.float32)
    x_centers = bounds[0, 0] + (np.arange(shape[0], dtype=np.float64) + 0.5) * pitch
    y_centers = bounds[0, 1] + (np.arange(shape[1], dtype=np.float64) + 0.5) * pitch
    z_centers = bounds[0, 2] + (np.arange(shape[2], dtype=np.float64) + 0.5) * pitch
    sample_offsets = np.array((-0.375, 0.0, 0.375), dtype=np.float64) * pitch
    sample_grids = []
    for x_offset in sample_offsets:
        for z_offset in sample_offsets:
            grid_x, grid_z = np.meshgrid(x_centers + x_offset, z_centers + z_offset, indexing="ij")
            sample_grids.append(np.column_stack([grid_x.ravel(), grid_z.ravel()]))
    occupancy = np.zeros(tuple(int(value) for value in shape), dtype=bool)
    tolerance = max(float(pitch) * 0.05, 1e-8)
    for y_index, y_value in enumerate(y_centers):
        section = mesh.section(plane_origin=[0.0, float(y_value), 0.0], plane_normal=[0.0, 1.0, 0.0])
        if section is None:
            continue
        contours = [np.asarray(path[:, [0, 2]], dtype=np.float64) for path in section.discrete if len(path) >= 3]
        if contours:
            coverage = np.zeros(shape[0] * shape[2], dtype=np.int16)
            for layer_points in sample_grids:
                coverage += _points_inside_contours(layer_points, contours, tolerance)
            occupancy[:, y_index, :] = (coverage >= 2).reshape(shape[0], shape[2])
    point_grid = np.zeros((*occupancy.shape, 3), dtype=np.float32)
    indices = np.argwhere(occupancy)
    if len(indices):
        point_grid[occupancy] = origin + (indices.astype(np.float32) + 0.5) * float(pitch)
    return occupancy, origin, point_grid


def voxelize_mesh_with_surface_fill(mesh, pitch: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    bounds = np.asarray(mesh.bounds, dtype=np.float64)
    extents = np.asarray(mesh.extents, dtype=np.float64)
    shape = np.maximum(1, np.ceil(extents / pitch).astype(int))
    origin = bounds[0].astype(np.float32)
    occupancy = np.zeros(tuple(int(value) for value in shape), dtype=bool)

    voxel_grid = mesh.voxelized(pitch=pitch).fill()
    if len(voxel_grid.points):
        indices = np.floor((np.asarray(voxel_grid.points, dtype=np.float64) - bounds[0]) / pitch).astype(int)
        indices = np.clip(indices, 0, shape - 1)
        occupancy[indices[:, 0], indices[:, 1], indices[:, 2]] = True

    point_grid = np.zeros((*occupancy.shape, 3), dtype=np.float32)
    occupied_indices = np.argwhere(occupancy)
    if len(occupied_indices):
        point_grid[occupancy] = origin + (occupied_indices.astype(np.float32) + 0.5) * float(pitch)
    return occupancy, origin, point_grid


def voxelize_mesh(
    mesh,
    output_path: Path,
    pitch: float,
    default_color_id: int = 16,
) -> VoxelArtifact:
    slice_occupancy, slice_origin, _slice_point_grid = voxelize_mesh_with_layer_slices(mesh, pitch)
    occupancy = slice_occupancy
    origin = slice_origin
    voxelizer = "slice"
    if not mesh.is_watertight:
        surface_occupancy, surface_origin, _surface_point_grid = voxelize_mesh_with_surface_fill(mesh, pitch)
        if int(surface_occupancy.sum()) > int(slice_occupancy.sum()) * 2:
            occupancy = surface_occupancy
            origin = surface_origin
            voxelizer = "surface"
    rgb = np.zeros((*occupancy.shape, 3), dtype=np.uint8)
    rgb[occupancy] = (160, 165, 169)
    color_ids = np.where(occupancy, int(default_color_id), 0).astype(np.int32)
    return save_voxel_artifact(output_path, occupancy, color_ids, rgb, origin, pitch, voxelizer=voxelizer)
