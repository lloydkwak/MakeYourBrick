from __future__ import annotations

import numpy as np

from makeyourbrick.brickify.optimizer import bricks_to_occupancy, layered_brickify
from makeyourbrick.sculpture.catalog import BrickCatalog
from makeyourbrick.sculpture.model import LayeredBrickModel, VoxelModel


def place_layered_bricks(
    target: VoxelModel,
    catalog: BrickCatalog,
    *,
    allow_rotations: bool = True,
) -> LayeredBrickModel:
    bricks = layered_brickify(
        target.occupancy,
        target.color_ids,
        brick_specs=catalog.specs,
        allow_rotations=allow_rotations,
    )
    return LayeredBrickModel.from_bricks(bricks)


def layered_model_occupancy(
    model: LayeredBrickModel,
    shape: tuple[int, int, int],
) -> np.ndarray:
    return bricks_to_occupancy(model.bricks(), shape)


def layered_model_matches_target(
    model: LayeredBrickModel,
    target: VoxelModel,
) -> bool:
    return bool(np.array_equal(layered_model_occupancy(model, target.shape), target.occupancy))
