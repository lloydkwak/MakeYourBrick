from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from makeyourbrick.brickify.colors import (
    load_ldraw_palette,
    quantize_rgb_to_ldraw,
    quantize_voxel_rgb_to_ldraw,
    validate_palette_rows,
)


def test_load_ldraw_palette_returns_ids_and_rgb_arrays() -> None:
    ids, rgb = load_ldraw_palette(Path("data/ldraw/ldraw_colors.json"))

    assert ids.ndim == 1
    assert rgb.shape == (len(ids), 3)
    assert ids.dtype == np.int32
    assert rgb.dtype == np.uint8


def test_validate_palette_rows_rejects_duplicate_ids() -> None:
    rows = [
        {"id": 4, "name": "Red", "rgb": [201, 26, 9]},
        {"id": 4, "name": "Also Red", "rgb": [201, 26, 9]},
    ]

    with pytest.raises(ValueError, match="Duplicate"):
        validate_palette_rows(rows)


def test_load_ldraw_palette_rejects_invalid_rgb_values() -> None:
    path = Path("outputs/test_invalid_colors.json")
    try:
        path.write_text(
            json.dumps([{"id": 14, "name": "Yellow", "rgb": [242, 205, 999]}]),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="RGB channels"):
            load_ldraw_palette(path)
    finally:
        path.unlink(missing_ok=True)


def test_quantize_rgb_to_ldraw_maps_known_colors_to_expected_ids() -> None:
    ids, palette_rgb = load_ldraw_palette(Path("data/ldraw/ldraw_colors.json"))
    rgb = np.asarray(
        [
            [[242, 205, 55], [201, 26, 9]],
            [[0, 85, 191], [242, 243, 242]],
        ],
        dtype=np.uint8,
    )

    color_ids = quantize_rgb_to_ldraw(rgb, ids, palette_rgb)

    np.testing.assert_array_equal(color_ids, np.asarray([[14, 4], [1, 15]], dtype=np.int32))


def test_quantize_rgb_to_ldraw_rejects_missing_channel_dimension() -> None:
    ids, palette_rgb = load_ldraw_palette(Path("data/ldraw/ldraw_colors.json"))

    with pytest.raises(ValueError, match="final channel"):
        quantize_rgb_to_ldraw(np.ones((2, 2), dtype=np.uint8), ids, palette_rgb)


def test_quantize_voxel_rgb_to_ldraw_only_assigns_occupied_voxels() -> None:
    ids, palette_rgb = load_ldraw_palette(Path("data/ldraw/ldraw_colors.json"))
    occupancy = np.asarray([[[True, False], [True, False]]], dtype=bool)
    rgb = np.zeros((*occupancy.shape, 3), dtype=np.uint8)
    rgb[0, 0, 0] = (242, 205, 55)
    rgb[0, 1, 0] = (201, 26, 9)

    color_ids = quantize_voxel_rgb_to_ldraw(
        occupancy,
        rgb,
        ids,
        palette_rgb,
        default_color_id=16,
    )

    assert color_ids[0, 0, 0] == 14
    assert color_ids[0, 1, 0] == 4
    assert color_ids[0, 0, 1] == 16
