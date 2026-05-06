from __future__ import annotations

import numpy as np

from makeyourbrick.types import Brick, BrickSpec


DEFAULT_BRICKS = (
    BrickSpec("3001.dat", 2, 4),
    BrickSpec("3010.dat", 1, 4),
    BrickSpec("3003.dat", 2, 2),
    BrickSpec("3004.dat", 1, 2),
    BrickSpec("3005.dat", 1, 1),
)


def _validate_voxel_inputs(occupancy: np.ndarray, color_ids: np.ndarray) -> None:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    if color_ids.shape != occupancy.shape:
        raise ValueError("Color id array must have the same shape as occupancy.")


def iter_occupied_voxels(occupancy: np.ndarray):
    """Yield occupied voxel coordinates bottom-up, then depth, then width."""
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    width, height, depth = occupancy.shape
    for y in range(height):
        for z in range(depth):
            for x in range(width):
                if occupancy[x, y, z]:
                    yield x, y, z


def brickify_1x1(occupancy: np.ndarray, color_ids: np.ndarray, part_id: str = "3005.dat") -> list[Brick]:
    _validate_voxel_inputs(occupancy, color_ids)
    bricks: list[Brick] = []
    for x, y, z in iter_occupied_voxels(occupancy):
        bricks.append(
            Brick(
                part_id=part_id,
                color_id=int(color_ids[x, y, z]),
                x=int(x),
                y=int(y),
                z=int(z),
                width=1,
                depth=1,
            )
        )
    return bricks


def greedy_brickify(occupancy: np.ndarray, color_ids: np.ndarray) -> list[Brick]:
    _ = DEFAULT_BRICKS
    return brickify_1x1(occupancy, color_ids)


def bricks_to_occupancy(bricks: list[Brick], shape: tuple[int, int, int]) -> np.ndarray:
    occupancy = np.zeros(shape, dtype=bool)
    for brick in bricks:
        x_slice = slice(brick.x, brick.x + brick.width)
        y_slice = slice(brick.y, brick.y + brick.height)
        z_slice = slice(brick.z, brick.z + brick.depth)
        occupancy[x_slice, y_slice, z_slice] = True
    return occupancy
