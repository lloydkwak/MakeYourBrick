from __future__ import annotations

import numpy as np

from makeyourbrick.brickify.optimizer import (
    COMPACT_SCULPTURE_BRICKS,
    PLATE_SCULPTURE_BRICKS,
    STUDIO_SCULPTURE_BRICKS,
    brick_specs_for_palette,
    brickify_1x1,
    bricks_to_occupancy,
    can_place_brick,
    greedy_brickify,
    horizontal_boundary_ratio,
    layered_brickify,
    layered_candidate_score,
    seam_overlap_ratio,
    support_ratio_for_area,
)
from makeyourbrick.types import Brick
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


def test_greedy_brickify_uses_longer_studio_style_bricks() -> None:
    occupancy, color_ids = make_solid_box((2, 1, 8), color_id=16)

    optimized = greedy_brickify(occupancy, color_ids)

    assert len(optimized) == 1
    assert optimized[0].part_id == "3007.dat"
    assert optimized[0].width == 2
    assert optimized[0].depth == 8
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)


def test_studio_brick_palette_excludes_2x10_and_preserves_occupancy() -> None:
    occupancy, color_ids = make_solid_box((2, 1, 10), color_id=16)

    optimized = greedy_brickify(occupancy, color_ids, brick_specs=STUDIO_SCULPTURE_BRICKS)

    assert "3006.dat" not in {brick.part_id for brick in optimized}
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)


def test_compact_brick_palette_limits_long_visual_spans() -> None:
    occupancy, color_ids = make_solid_box((2, 1, 8), color_id=16)

    optimized = greedy_brickify(occupancy, color_ids, brick_specs=COMPACT_SCULPTURE_BRICKS)

    assert max(max(brick.width, brick.depth) for brick in optimized) <= 4
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)


def test_plate_brick_palette_uses_plate_parts() -> None:
    occupancy, color_ids = make_solid_box((2, 1, 4), color_id=16)

    optimized = greedy_brickify(occupancy, color_ids, brick_specs=PLATE_SCULPTURE_BRICKS)

    assert optimized[0].part_id == "3020.dat"
    assert all(brick.height == 1 for brick in optimized)
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)


def test_brick_specs_for_palette_validates_names() -> None:
    assert brick_specs_for_palette("studio") == STUDIO_SCULPTURE_BRICKS
    assert brick_specs_for_palette("compact") == COMPACT_SCULPTURE_BRICKS
    assert brick_specs_for_palette("plates") == PLATE_SCULPTURE_BRICKS
    assert brick_specs_for_palette("full")


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


def test_support_ratio_for_area_detects_partial_support() -> None:
    used = np.zeros((3, 2, 3), dtype=bool)
    used[0, 0, 0] = True
    used[1, 0, 0] = True

    assert support_ratio_for_area(used, 0, 1, 0, 2, 2) == 0.5
    assert support_ratio_for_area(used, 0, 0, 0, 2, 2) == 1.0


def test_horizontal_boundary_ratio_detects_outer_footprint_cells() -> None:
    occupancy, _color_ids = make_solid_box((5, 1, 5), color_id=16)

    assert horizontal_boundary_ratio(occupancy, 1, 0, 1, 3, 3) < 1.0
    assert horizontal_boundary_ratio(occupancy, 0, 0, 0, 5, 1) == 1.0


def test_seam_overlap_ratio_detects_aligned_edges() -> None:
    lower = [brickify_1x1(*make_solid_box((2, 1, 1), color_id=16))[0]]

    assert seam_overlap_ratio(lower, 1, 0, 0, 1, 1) > 0


def test_layered_brickify_preserves_occupancy_and_color_boundaries() -> None:
    occupancy, color_ids = make_solid_box((4, 2, 2), color_id=16)
    color_ids[2:, :, :] = 14

    optimized = layered_brickify(occupancy, color_ids)

    assert {brick.color_id for brick in optimized} == {14, 16}
    np.testing.assert_array_equal(bricks_to_occupancy(optimized, occupancy.shape), occupancy)


def test_layered_candidate_score_prefers_supported_smaller_brick_over_overhang() -> None:
    used = np.zeros((4, 2, 2), dtype=bool)
    used[0:2, 0, 0:2] = True

    supported_score = layered_candidate_score(
        placed_bricks=[],
        used=used,
        x=0,
        y=1,
        z=0,
        width=2,
        depth=2,
    )
    overhang_score = layered_candidate_score(
        placed_bricks=[],
        used=used,
        x=0,
        y=1,
        z=0,
        width=4,
        depth=2,
    )

    assert supported_score > overhang_score


def test_layered_candidate_score_penalizes_vertical_seam_alignment() -> None:
    used = np.ones((2, 2, 2), dtype=bool)
    lower_bricks = [Brick("3003.dat", 16, 0, 0, 0, width=2, depth=2)]

    aligned_score = layered_candidate_score(
        placed_bricks=lower_bricks,
        used=used,
        x=0,
        y=1,
        z=0,
        width=2,
        depth=2,
    )
    no_lower_seam_score = layered_candidate_score(
        placed_bricks=[],
        used=used,
        x=0,
        y=1,
        z=0,
        width=2,
        depth=2,
    )

    assert aligned_score < no_lower_seam_score


def test_layered_candidate_score_penalizes_long_boundary_bricks() -> None:
    occupancy, _color_ids = make_solid_box((8, 1, 4), color_id=16)
    used = np.ones_like(occupancy, dtype=bool)

    short_boundary = layered_candidate_score(
        placed_bricks=[],
        used=used,
        occupancy=occupancy,
        x=0,
        y=0,
        z=0,
        width=4,
        depth=1,
    )
    long_boundary = layered_candidate_score(
        placed_bricks=[],
        used=used,
        occupancy=occupancy,
        x=0,
        y=0,
        z=0,
        width=8,
        depth=1,
    )

    assert short_boundary > long_boundary
