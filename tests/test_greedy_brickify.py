from __future__ import annotations

import numpy as np

from makeyourbrick.brickify.optimizer import (
    brickify_1x1,
    bricks_to_occupancy,
    can_place_brick,
    greedy_brickify,
)
from makeyourbrick.voxel.synthetic import make_solid_box


def test_can_place_brick_requires_same_color() -> None:
    occupancy, color_ids = make_solid_box((2, 1, 2), color_id=16)
    used = np.zeros_like(occupancy, dtype=bool)
    color_ids[1, 0, 1] = 14

    assert not can_place_brick(occupancy, used, color_ids, 0, 0, 0, 2, 2, 1, 16)


def test_greedy_brickify_reduces_uniform_box_to_one_2x4_brick() -> None:
    occupancy, color_ids = make_solid_box((2, 1, 4), color_id=16)

    one_by_one = brickify_1x1(occupancy, color_ids)
    optimized = greedy_brickify(occupancy, color_ids)

    assert len(one_by_one) == 8
    assert len(optimized) == 1
    assert optimized[0].part_id == "3001.dat"
    assert optimized[0].width == 2
    assert optimized[0].depth == 4
    assert optimized[0].rotation_degrees == 0
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)


def test_greedy_brickify_uses_rotation_when_it_makes_larger_brick_fit() -> None:
    occupancy, color_ids = make_solid_box((4, 1, 2), color_id=16)

    optimized = greedy_brickify(occupancy, color_ids)

    assert len(optimized) == 1
    assert optimized[0].part_id == "3001.dat"
    assert optimized[0].width == 4
    assert optimized[0].depth == 2
    assert optimized[0].rotation_degrees == 90
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)


def test_greedy_brickify_does_not_merge_across_color_boundaries() -> None:
    occupancy, color_ids = make_solid_box((4, 1, 2), color_id=16)
    color_ids[2:, :, :] = 14

    optimized = greedy_brickify(occupancy, color_ids)

    assert len(optimized) == 2
    assert {brick.color_id for brick in optimized} == {14, 16}
    assert all(brick.part_id == "3003.dat" for brick in optimized)
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)


def test_greedy_brickify_preserves_sparse_occupancy() -> None:
    occupancy = np.zeros((3, 1, 3), dtype=bool)
    occupancy[0, 0, 0] = True
    occupancy[1, 0, 0] = True
    occupancy[2, 0, 2] = True
    color_ids = np.full(occupancy.shape, 4, dtype=np.int32)

    optimized = greedy_brickify(occupancy, color_ids)

    assert len(optimized) == 2
    assert {brick.part_id for brick in optimized} == {"3004.dat", "3005.dat"}
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)

