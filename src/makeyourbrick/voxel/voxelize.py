from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from makeyourbrick.types import VoxelArtifact


def compute_pitch(mesh: trimesh.Trimesh, target_longest_studs: int, min_pitch: float = 0.005) -> float:
    longest = float(mesh.extents.max())
    if longest <= 0:
        raise ValueError("Mesh has zero-sized bounds.")
    return max(longest / target_longest_studs, min_pitch)


def voxelize_mesh(mesh: trimesh.Trimesh, output_path: Path, pitch: float, fill: bool = True) -> VoxelArtifact:
    grid = mesh.voxelized(pitch)
    if fill:
        grid = grid.fill()
    occupancy = grid.matrix.astype(bool)
    rgb = np.zeros((*occupancy.shape, 3), dtype=np.uint8)
    rgb[occupancy] = (160, 165, 169)
    origin = np.asarray(grid.origin, dtype=np.float32)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output_path, occupancy=occupancy, rgb=rgb, origin=origin, pitch=np.float32(pitch))
    return VoxelArtifact(path=output_path, pitch=pitch, origin=tuple(float(v) for v in origin))

