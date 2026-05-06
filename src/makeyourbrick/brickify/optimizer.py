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


def brickify_1x1(occupancy: np.ndarray, color_ids: np.ndarray, part_id: str = "3005.dat") -> list[Brick]:
    bricks: list[Brick] = []
    for x, y, z in np.argwhere(occupancy):
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

