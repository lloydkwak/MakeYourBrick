from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.brickify.colors import load_ldraw_palette
from makeyourbrick.voxel.voxelize import (
    compute_pitch,
    load_voxel_artifact,
    save_voxel_artifact,
    voxelize_mesh,
)


def test_compute_pitch_scales_longest_extent_to_target_studs() -> None:
    mesh = trimesh.creation.box(extents=(2, 4, 1))

    assert compute_pitch(mesh, target_longest_studs=8) == 0.5


def test_compute_pitch_respects_min_pitch() -> None:
    mesh = trimesh.creation.box(extents=(1, 1, 1))

    assert compute_pitch(mesh, target_longest_studs=1000, min_pitch=0.01) == 0.01


def test_save_and_load_voxel_artifact_round_trip() -> None:
    output_path = Path("outputs/voxels/test_voxel_artifact.npz")
    occupancy = np.ones((2, 3, 4), dtype=bool)
    color_ids = np.full(occupancy.shape, 14, dtype=np.int32)
    rgb = np.zeros((*occupancy.shape, 3), dtype=np.uint8)
    origin = np.asarray([1, 2, 3], dtype=np.float32)

    try:
        artifact = save_voxel_artifact(output_path, occupancy, color_ids, rgb, origin, pitch=0.25)
        loaded_occupancy, loaded_colors, loaded_rgb, loaded_origin, loaded_pitch = load_voxel_artifact(
            artifact.path
        )

        np.testing.assert_array_equal(loaded_occupancy, occupancy)
        np.testing.assert_array_equal(loaded_colors, color_ids)
        np.testing.assert_array_equal(loaded_rgb, rgb)
        np.testing.assert_array_equal(loaded_origin, origin)
        assert loaded_pitch == pytest.approx(0.25)
    finally:
        output_path.unlink(missing_ok=True)


def test_voxelize_mesh_writes_occupancy_and_default_color_ids() -> None:
    output_path = Path("outputs/voxels/test_box_voxels.npz")
    mesh = trimesh.creation.box(extents=(1, 1, 1))

    try:
        artifact = voxelize_mesh(mesh, output_path, pitch=0.5, fill=True, default_color_id=4)
        occupancy, color_ids, rgb, _origin, pitch = load_voxel_artifact(artifact.path)

        assert occupancy.ndim == 3
        assert occupancy.any()
        assert np.all(color_ids[occupancy] == 4)
        assert rgb.shape == (*occupancy.shape, 3)
        assert pitch == pytest.approx(0.5)
    finally:
        output_path.unlink(missing_ok=True)


def test_voxelize_mesh_quantizes_constant_rgb_when_palette_is_provided() -> None:
    output_path = Path("outputs/voxels/test_box_yellow_voxels.npz")
    mesh = trimesh.creation.box(extents=(1, 1, 1))
    palette_ids, palette_rgb = load_ldraw_palette(Path("data/ldraw/ldraw_colors.json"))

    try:
        artifact = voxelize_mesh(
            mesh,
            output_path,
            pitch=0.5,
            fill=True,
            default_rgb=(242, 205, 55),
            palette_ids=palette_ids,
            palette_rgb=palette_rgb,
        )
        occupancy, color_ids, rgb, _origin, _pitch = load_voxel_artifact(artifact.path)

        assert occupancy.any()
        assert np.all(color_ids[occupancy] == 14)
        assert np.all(rgb[occupancy] == np.asarray([242, 205, 55], dtype=np.uint8))
    finally:
        output_path.unlink(missing_ok=True)
