from __future__ import annotations

import numpy as np
import pytest

from makeyourbrick.voxel.synthetic import make_solid_box, make_stairs


def test_make_solid_box_returns_filled_occupancy_and_colors() -> None:
    occupancy, color_ids = make_solid_box((4, 3, 2), color_id=14)

    assert occupancy.shape == (4, 3, 2)
    assert color_ids.shape == occupancy.shape
    assert occupancy.dtype == np.bool_
    assert occupancy.sum() == 24
    assert np.all(color_ids[occupancy] == 14)


def test_make_solid_box_rejects_empty_dimensions() -> None:
    with pytest.raises(ValueError, match="positive"):
        make_solid_box((4, 0, 2))


def test_make_stairs_removes_one_x_column_per_layer() -> None:
    occupancy, color_ids = make_stairs(width=4, steps=3, depth=2, color_id=4)

    assert occupancy.shape == (4, 3, 2)
    assert occupancy[:, 0, :].sum() == 8
    assert occupancy[:, 1, :].sum() == 6
    assert occupancy[:, 2, :].sum() == 4
    assert np.all(color_ids[occupancy] == 4)

