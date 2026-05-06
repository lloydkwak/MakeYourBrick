from __future__ import annotations

from pathlib import Path

import numpy as np

try:
    import trimesh
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps are absent.
    trimesh = None

from makeyourbrick.brickify.colors import quantize_voxel_rgb_to_ldraw
from makeyourbrick.types import VoxelArtifact


def compute_pitch(mesh, target_longest_studs: int, min_pitch: float = 0.005) -> float:
    if target_longest_studs <= 0:
        raise ValueError("target_longest_studs must be positive.")
    longest = float(mesh.extents.max())
    if longest <= 0:
        raise ValueError("Mesh has zero-sized bounds.")
    return max(longest / target_longest_studs, min_pitch)


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


def voxelize_mesh(
    mesh,
    output_path: Path,
    pitch: float,
    fill: bool = True,
    default_color_id: int = 16,
    default_rgb: tuple[int, int, int] | None = None,
    palette_ids: np.ndarray | None = None,
    palette_rgb: np.ndarray | None = None,
) -> VoxelArtifact:
    grid = mesh.voxelized(pitch)
    if fill:
        grid = grid.fill()
    occupancy = grid.matrix.astype(bool)
    rgb = np.zeros((*occupancy.shape, 3), dtype=np.uint8)
    rgb_value = default_rgb or (160, 165, 169)
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
    origin = voxel_grid_origin(grid)
    return save_voxel_artifact(output_path, occupancy, color_ids, rgb, origin, pitch)
