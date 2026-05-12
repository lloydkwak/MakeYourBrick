from __future__ import annotations

import numpy as np
import pytest

from makeyourbrick.sculpture import (
    LayeredBrickModel,
    SculptureSettings,
    VoxelModel,
    catalog_for_palette,
)
from makeyourbrick.types import Brick


def test_voxel_model_validates_shape_and_counts() -> None:
    occupancy = np.ones((2, 3, 4), dtype=bool)
    color_ids = np.full(occupancy.shape, 16, dtype=np.int32)

    model = VoxelModel(occupancy, color_ids, pitch=0.5, origin=(0.0, 0.0, 0.0))

    assert model.shape == (2, 3, 4)
    assert model.occupied_count == 24


def test_voxel_model_requires_matching_color_shape() -> None:
    with pytest.raises(ValueError, match="color_ids"):
        VoxelModel(
            np.ones((2, 2, 2), dtype=bool),
            np.ones((2, 2, 1), dtype=np.int32),
            pitch=1.0,
            origin=(0.0, 0.0, 0.0),
        )


def test_sculpture_settings_validate_wall_and_base() -> None:
    settings = SculptureSettings(
        base_size_studs=32,
        wall_thickness=2,
        base_thickness=1,
        brick_palette="compact",
    )

    assert settings.steps_by_layer is True

    with pytest.raises(ValueError, match="wall_thickness"):
        SculptureSettings(wall_thickness=0)


def test_layered_brick_model_groups_bricks_by_layer() -> None:
    bricks = [
        Brick("3005.dat", 16, 0, 1, 0, 1, 1),
        Brick("3005.dat", 16, 0, 0, 0, 1, 1),
    ]

    model = LayeredBrickModel.from_bricks(bricks)

    assert list(model.bricks_by_layer) == [0, 1]
    assert model.layer_count == 2
    assert model.brick_count == 2
    assert [brick.y for brick in model.bricks()] == [0, 1]


def test_catalog_for_palette_exposes_expected_sets() -> None:
    compact = catalog_for_palette("compact")
    plates = catalog_for_palette("plates")

    assert compact.max_span == 4
    assert "3001.dat" in compact.part_ids
    assert "3020.dat" in plates.part_ids

