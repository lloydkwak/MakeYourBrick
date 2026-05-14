from __future__ import annotations

from dataclasses import replace
from typing import Literal

import numpy as np

from makeyourbrick.brickify.optimizer import (
    bricks_to_occupancy,
    reward_layered_brickify,
    reward_layered_surface_brickify,
    run_length_layered_brickify,
)
from makeyourbrick.sculpture.catalog import BrickCatalog
from makeyourbrick.sculpture.model import LayeredBrickModel, VoxelModel
from makeyourbrick.types import Brick

STUDIO_LAYER_COLOR_IDS = (1, 2, 3, 13, 15, 19, 20, 27)

ColorStrategy = Literal["strict", "majority", "layer"]
PlacementMode = Literal["solid", "surface", "run"]


def assign_brick_colors_by_majority(
    bricks: list[Brick],
    color_ids: np.ndarray,
    *,
    default_color_id: int = 16,
) -> list[Brick]:
    colored_bricks: list[Brick] = []
    for brick in bricks:
        colors = color_ids[
            brick.x : brick.x + brick.width,
            brick.y : brick.y + brick.height,
            brick.z : brick.z + brick.depth,
        ]
        colors = colors[colors > 0]
        if len(colors):
            values, counts = np.unique(colors, return_counts=True)
            color_id = int(values[int(np.argmax(counts))])
        else:
            color_id = int(default_color_id)
        colored_bricks.append(replace(brick, color_id=color_id))
    return colored_bricks


def assign_brick_colors_by_layer(
    bricks: list[Brick],
    *,
    layer_color_ids: tuple[int, ...] = STUDIO_LAYER_COLOR_IDS,
) -> list[Brick]:
    if not layer_color_ids:
        raise ValueError("layer_color_ids must not be empty.")
    return [
        replace(brick, color_id=int(layer_color_ids[brick.y % len(layer_color_ids)]))
        for brick in bricks
    ]


def place_layered_bricks(
    target: VoxelModel,
    catalog: BrickCatalog,
    *,
    allow_rotations: bool = True,
    color_strategy: ColorStrategy = "strict",
    placement_mode: PlacementMode = "solid",
    min_coverage_ratio: float = 0.2,
    strict_coverage: bool = False,
    default_color_id: int = 16,
) -> LayeredBrickModel:
    if color_strategy not in {"strict", "majority", "layer"}:
        raise ValueError(f"Unsupported color strategy: {color_strategy}")
    if placement_mode not in {"solid", "surface", "run"}:
        raise ValueError(f"Unsupported placement mode: {placement_mode}")
    placement_colors = target.color_ids
    if color_strategy in {"majority", "layer"}:
        placement_colors = np.where(target.occupancy, int(default_color_id), 0).astype(np.int32)
    if placement_mode == "surface":
        bricks = reward_layered_surface_brickify(
            target.occupancy,
            placement_colors,
            brick_specs=catalog.specs,
            allow_rotations=allow_rotations,
            min_coverage_ratio=min_coverage_ratio,
            strict_coverage=strict_coverage,
        )
    elif placement_mode == "run":
        bricks = run_length_layered_brickify(
            target.occupancy,
            placement_colors,
            brick_specs=catalog.specs,
            allow_rotations=allow_rotations,
        )
    else:
        bricks = reward_layered_brickify(
            target.occupancy,
            placement_colors,
            brick_specs=catalog.specs,
            allow_rotations=allow_rotations,
        )
    if color_strategy == "majority":
        bricks = assign_brick_colors_by_majority(
            bricks,
            target.color_ids,
            default_color_id=default_color_id,
        )
    elif color_strategy == "layer":
        bricks = assign_brick_colors_by_layer(bricks)
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
