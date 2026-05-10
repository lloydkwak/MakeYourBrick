from __future__ import annotations

import numpy as np
import pytest

from makeyourbrick.voxel.sculpture import apply_sculpture_mode, surface_mask


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


def test_sculpture_mode_validates_inputs() -> None:
    occupancy = np.ones((2, 2, 2), dtype=bool)
    color_ids = np.ones((2, 2, 2), dtype=np.int32)

    with pytest.raises(ValueError, match="wall_thickness"):
        apply_sculpture_mode(occupancy, color_ids, mode="shell", wall_thickness=0)

    with pytest.raises(ValueError, match="Unsupported"):
        apply_sculpture_mode(occupancy, color_ids, mode="hollow")
