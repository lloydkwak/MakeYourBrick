from __future__ import annotations

import numpy as np
import pytest

from makeyourbrick.brickify.optimizer import brickify_1x1, bricks_to_occupancy
from makeyourbrick.voxel.synthetic import make_solid_box, make_stairs


def test_brickify_1x1_emits_one_brick_per_occupied_voxel() -> None:
    occupancy, color_ids = make_solid_box((3, 2, 2), color_id=14)

    bricks = brickify_1x1(occupancy, color_ids)

    assert len(bricks) == int(occupancy.sum())
    assert {brick.part_id for brick in bricks} == {"3005.dat"}
    assert {brick.color_id for brick in bricks} == {14}


def test_brickify_1x1_uses_bottom_up_deterministic_order() -> None:
    occupancy = np.zeros((2, 2, 2), dtype=bool)
    occupancy[1, 0, 0] = True
    occupancy[0, 0, 1] = True
    occupancy[0, 1, 0] = True
    color_ids = np.full(occupancy.shape, 16, dtype=np.int32)

    bricks = brickify_1x1(occupancy, color_ids)

    assert [(brick.x, brick.y, brick.z) for brick in bricks] == [
        (1, 0, 0),
        (0, 0, 1),
        (0, 1, 0),
    ]


def test_bricks_to_occupancy_round_trip_matches_original_shape() -> None:
    occupancy, color_ids = make_stairs(width=4, steps=3, depth=2, color_id=4)

    bricks = brickify_1x1(occupancy, color_ids)
    reconstructed = bricks_to_occupancy(bricks, occupancy.shape)

    np.testing.assert_array_equal(reconstructed, occupancy)


def test_brickify_1x1_rejects_mismatched_color_shape() -> None:
    occupancy = np.ones((2, 2, 2), dtype=bool)
    color_ids = np.ones((2, 2, 1), dtype=np.int32)

    with pytest.raises(ValueError, match="same shape"):
        brickify_1x1(occupancy, color_ids)

