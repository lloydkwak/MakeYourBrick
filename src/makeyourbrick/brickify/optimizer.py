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


def candidate_orientations(spec: BrickSpec, allow_rotations: bool = True) -> tuple[tuple[int, int, int], ...]:
    orientations = [(spec.width, spec.depth, 0)]
    if allow_rotations and spec.width != spec.depth:
        orientations.append((spec.depth, spec.width, 90))
    return tuple(orientations)


def can_place_brick(
    occupancy: np.ndarray,
    used: np.ndarray,
    color_ids: np.ndarray,
    x: int,
    y: int,
    z: int,
    width: int,
    depth: int,
    height: int,
    color_id: int,
) -> bool:
    max_x, max_y, max_z = occupancy.shape
    if x + width > max_x or y + height > max_y or z + depth > max_z:
        return False
    x_slice = slice(x, x + width)
    y_slice = slice(y, y + height)
    z_slice = slice(z, z + depth)
    volume = occupancy[x_slice, y_slice, z_slice]
    if not volume.all():
        return False
    if used[x_slice, y_slice, z_slice].any():
        return False
    return bool((color_ids[x_slice, y_slice, z_slice] == color_id).all())


def mark_used(used: np.ndarray, brick: Brick) -> None:
    used[
        brick.x : brick.x + brick.width,
        brick.y : brick.y + brick.height,
        brick.z : brick.z + brick.depth,
    ] = True


def greedy_brickify(
    occupancy: np.ndarray,
    color_ids: np.ndarray,
    brick_specs: tuple[BrickSpec, ...] = DEFAULT_BRICKS,
    allow_rotations: bool = True,
) -> list[Brick]:
    _validate_voxel_inputs(occupancy, color_ids)
    used = np.zeros_like(occupancy, dtype=bool)
    bricks: list[Brick] = []

    for x, y, z in iter_occupied_voxels(occupancy):
        if used[x, y, z]:
            continue
        color_id = int(color_ids[x, y, z])
        placed = False
        for spec in brick_specs:
            for width, depth, rotation_degrees in candidate_orientations(spec, allow_rotations):
                if can_place_brick(
                    occupancy,
                    used,
                    color_ids,
                    x,
                    y,
                    z,
                    width,
                    depth,
                    spec.height,
                    color_id,
                ):
                    brick = Brick(
                        part_id=spec.part_id,
                        color_id=color_id,
                        x=int(x),
                        y=int(y),
                        z=int(z),
                        width=int(width),
                        depth=int(depth),
                        height=int(spec.height),
                        rotation_degrees=rotation_degrees,
                    )
                    bricks.append(brick)
                    mark_used(used, brick)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            brick = Brick(
                part_id="3005.dat",
                color_id=color_id,
                x=int(x),
                y=int(y),
                z=int(z),
                width=1,
                depth=1,
            )
            bricks.append(brick)
            mark_used(used, brick)
    return bricks


def bricks_to_occupancy(bricks: list[Brick], shape: tuple[int, int, int]) -> np.ndarray:
    occupancy = np.zeros(shape, dtype=bool)
    for brick in bricks:
        x_slice = slice(brick.x, brick.x + brick.width)
        y_slice = slice(brick.y, brick.y + brick.height)
        z_slice = slice(brick.z, brick.z + brick.depth)
        occupancy[x_slice, y_slice, z_slice] = True
    return occupancy
