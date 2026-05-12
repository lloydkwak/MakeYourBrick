from __future__ import annotations

import numpy as np
import pytest

from makeyourbrick.sculpture import (
    LayeredBrickModel,
    SculptureSettings,
    VoxelModel,
    build_contour_shell_targets,
    catalog_for_palette,
    plan_sparse_support_columns,
)
from makeyourbrick.types import Brick
from makeyourbrick.voxel.sculpture import base_fill_mask, contour_shell_mask


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

    with pytest.raises(ValueError, match="support_spacing"):
        SculptureSettings(support_spacing=0)


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


def test_contour_shell_targets_keep_base_shell_and_support_separate() -> None:
    occupancy = np.ones((5, 4, 5), dtype=bool)
    colors = np.full(occupancy.shape, 16, dtype=np.int32)
    model = VoxelModel(occupancy, colors, pitch=1.0, origin=(0.0, 0.0, 0.0))

    targets = build_contour_shell_targets(
        model,
        SculptureSettings(wall_thickness=1, base_thickness=1, support_spacing=3),
    )

    assert targets.base.occupancy[:, 0, :].all()
    assert not targets.shell.occupancy[2, 2, 2]
    assert not targets.target.occupancy[2, 2, 2]
    assert np.all(targets.target.occupancy <= targets.solid.occupancy)
    assert not (targets.support.occupancy & targets.shell.occupancy).any()
    assert not (targets.support.occupancy & targets.base.occupancy).any()


def test_contour_shell_targets_add_sparse_support_for_overhangs() -> None:
    occupancy = np.zeros((5, 3, 5), dtype=bool)
    occupancy[:, 0:2, :] = True
    occupancy[2, 2, 2] = True
    colors = np.full(occupancy.shape, 16, dtype=np.int32)
    model = VoxelModel(occupancy, colors, pitch=1.0, origin=(0.0, 0.0, 0.0))

    targets = build_contour_shell_targets(
        model,
        SculptureSettings(wall_thickness=1, base_thickness=1, support_spacing=1),
    )

    assert targets.support.occupied_count > 0
    assert np.all(targets.target.occupancy <= occupancy)
    assert targets.target.color_ids[targets.target.occupancy].min() == 16


def test_sparse_support_planner_uses_fewer_columns_at_wider_spacing() -> None:
    solid = np.zeros((7, 3, 7), dtype=bool)
    solid[:, 0:2, :] = True
    solid[2:5, 2, 2:5] = True
    shell = contour_shell_mask(solid, wall_thickness=1)
    target = shell | base_fill_mask(solid, base_thickness=1)

    dense = plan_sparse_support_columns(target, solid, base_thickness=1, support_spacing=1)
    sparse = plan_sparse_support_columns(target, solid, base_thickness=1, support_spacing=3)

    assert 0 < sparse.sum() < dense.sum()
    assert np.all(sparse <= solid)
