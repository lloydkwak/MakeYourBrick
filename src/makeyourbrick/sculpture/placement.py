from __future__ import annotations

from dataclasses import replace

import numpy as np

from makeyourbrick.brickify.optimizer import bricks_to_occupancy, run_length_layered_brickify
from makeyourbrick.sculpture.catalog import BrickCatalog
from makeyourbrick.sculpture.model import LayeredBrickModel, VoxelModel
from makeyourbrick.types import Brick

STUDIO_LAYER_COLOR_IDS = (15, 3, 2, 19, 20, 27, 13, 1)


def assign_brick_colors_by_layer(
    bricks: list[Brick],
    *,
    layer_color_ids: tuple[int, ...] = STUDIO_LAYER_COLOR_IDS,
) -> list[Brick]:
    if not layer_color_ids:
        raise ValueError("layer_color_ids must not be empty.")
    return [replace(brick, color_id=int(layer_color_ids[brick.y % len(layer_color_ids)])) for brick in bricks]


def place_layered_bricks(target: VoxelModel, catalog: BrickCatalog, color_strategy: str = "layer") -> LayeredBrickModel:
    if color_strategy == "layer":
        placement_colors = np.where(target.occupancy, 16, 0).astype(np.int32)
    elif color_strategy == "mesh":
        placement_colors = target.color_ids
    else:
        raise ValueError("color_strategy must be 'layer' or 'mesh'.")
    bricks = run_length_layered_brickify(
        target.occupancy,
        placement_colors,
        brick_specs=catalog.specs,
        allow_rotations=True,
    )
    if color_strategy == "layer":
        bricks = assign_brick_colors_by_layer(bricks)
    return LayeredBrickModel.from_bricks(bricks)


def layered_model_occupancy(model: LayeredBrickModel, shape: tuple[int, int, int]) -> np.ndarray:
    return bricks_to_occupancy(model.bricks(), shape)


def layered_model_matches_target(model: LayeredBrickModel, target: VoxelModel) -> bool:
    return bool(np.array_equal(layered_model_occupancy(model, target.shape), target.occupancy))
