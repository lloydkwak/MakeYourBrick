from __future__ import annotations

import numpy as np
import pytest

from makeyourbrick.voxel.sculpture import (
    anchor_shell_to_base,
    apply_sculpture_mode,
    fill_2d_holes,
    fill_horizontal_layer_holes,
    preprocess_shell_occupancy,
    preprocess_solid_occupancy,
    surface_mask,
)


def test_surface_mask_detects_boundary_voxels() -> None:
    occupancy = np.ones((3, 3, 3), dtype=bool)

    surface = surface_mask(occupancy)

    assert surface.sum() == 26
    assert not surface[1, 1, 1]


def test_shell_mode_removes_interior_voxels_and_preserves_colors() -> None:
    occupancy = np.ones((3, 3, 3), dtype=bool)
    color_ids = np.full(occupancy.shape, 14, dtype=np.int32)
    color_ids[1, 1, 1] = 4

    shell, shell_colors = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode="shell",
        wall_thickness=1,
        base_thickness=0,
    )

    assert shell.sum() == 26
    assert not shell[1, 1, 1]
    assert shell_colors[0, 0, 0] == 14
    assert shell_colors[1, 1, 1] == 0


def test_shell_mode_fills_requested_base_layers() -> None:
    occupancy = np.ones((5, 5, 5), dtype=bool)
    color_ids = np.full(occupancy.shape, 16, dtype=np.int32)

    shell, _colors = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode="shell",
        wall_thickness=1,
        base_thickness=2,
    )

    assert shell[:, 0, :].all()
    assert shell[:, 1, :].all()
    assert not shell[2, 2, 2]


def test_wall_thickness_can_retain_full_small_model() -> None:
    occupancy = np.ones((3, 3, 3), dtype=bool)
    color_ids = np.full(occupancy.shape, 16, dtype=np.int32)

    shell, _colors = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode="shell",
        wall_thickness=2,
        base_thickness=0,
    )

    assert shell.all()


def test_fill_2d_holes_fills_enclosed_layer_voids_only() -> None:
    layer = np.ones((5, 5), dtype=bool)
    layer[2, 2] = False
    layer[0, 2] = False

    filled = fill_2d_holes(layer)

    assert filled[2, 2]
    assert not filled[0, 2]


def test_solid_mode_fills_layer_holes_and_assigns_layer_color() -> None:
    occupancy = np.ones((5, 2, 5), dtype=bool)
    occupancy[2, 0, 2] = False
    color_ids = np.full(occupancy.shape, 14, dtype=np.int32)

    solid, solid_colors = apply_sculpture_mode(occupancy, color_ids, mode="solid")

    assert solid[2, 0, 2]
    assert solid_colors[2, 0, 2] == 14


def test_fill_horizontal_layer_holes_does_not_connect_open_boundaries() -> None:
    occupancy = np.zeros((5, 1, 5), dtype=bool)
    occupancy[1:4, 0, 1] = True
    occupancy[1:4, 0, 3] = True
    occupancy[1, 0, 1:4] = True

    filled = fill_horizontal_layer_holes(occupancy)

    assert not filled[2, 0, 2]


def test_preprocess_solid_occupancy_removes_isolated_voxels() -> None:
    occupancy = np.zeros((5, 1, 5), dtype=bool)
    occupancy[0, 0, 0] = True

    assert not preprocess_solid_occupancy(occupancy).any()


def test_shell_preprocess_closes_single_voxel_gaps_and_removes_isolated_features() -> None:
    occupancy = np.ones((3, 3, 3), dtype=bool)
    occupancy[1, 1, 1] = False
    occupancy[0, 0, 0] = False
    occupancy[2, 2, 2] = False
    occupancy = np.pad(occupancy, 1, mode="constant", constant_values=False)
    occupancy[0, 0, 0] = True

    processed = preprocess_shell_occupancy(occupancy)

    assert processed[2, 2, 2]
    assert not processed[0, 0, 0]


def test_shell_base_anchoring_adds_minimal_vertical_support() -> None:
    shell = np.zeros((3, 4, 3), dtype=bool)
    occupancy = np.zeros_like(shell)
    shell[1, 3, 1] = True
    occupancy[1, :, 1] = True
    shell[0, 0, 0] = True
    occupancy[0, 0, 0] = True

    anchored = anchor_shell_to_base(shell, occupancy, base_thickness=1)

    assert anchored[1, :, 1].all()
    assert anchored[0, 0, 0]


def test_sculpture_mode_validates_inputs() -> None:
    occupancy = np.ones((2, 2, 2), dtype=bool)
    color_ids = np.ones((2, 2, 2), dtype=np.int32)

    with pytest.raises(ValueError, match="wall_thickness"):
        apply_sculpture_mode(occupancy, color_ids, mode="shell", wall_thickness=0)

    with pytest.raises(ValueError, match="Unsupported"):
        apply_sculpture_mode(occupancy, color_ids, mode="hollow")
