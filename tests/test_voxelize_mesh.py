from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.brickify.colors import load_ldraw_palette
from makeyourbrick.voxel.voxelize import (
    _pair_ray_hit_intervals,
    _points_inside_contours,
    compute_pitch,
    load_voxel_artifact,
    save_voxel_artifact,
    voxelize_mesh_with_layer_slices,
    voxelize_mesh_with_vertical_rays,
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


def test_vertical_ray_voxelizer_fills_box_columns() -> None:
    mesh = trimesh.creation.box(extents=(1, 1, 1))

    occupancy, origin, _points = voxelize_mesh_with_vertical_rays(mesh, pitch=0.25)

    assert occupancy.ndim == 3
    assert occupancy.sum() > 0
    assert occupancy[:, 1:-1, :].any()
    assert origin.shape == (3,)


def test_points_inside_contours_uses_even_odd_holes() -> None:
    outer = np.asarray([[0, 0], [4, 0], [4, 4], [0, 4], [0, 0]], dtype=np.float64)
    inner = np.asarray([[1, 1], [1, 3], [3, 3], [3, 1], [1, 1]], dtype=np.float64)
    points = np.asarray([[0.5, 0.5], [2.0, 2.0], [4.5, 2.0]], dtype=np.float64)

    inside = _points_inside_contours(points, [outer, inner], tolerance=1e-8)

    np.testing.assert_array_equal(inside, np.asarray([True, False, False]))


def test_layer_slice_voxelizer_fills_box_layers() -> None:
    mesh = trimesh.creation.box(extents=(1, 1, 1))

    occupancy, origin, _points = voxelize_mesh_with_layer_slices(mesh, pitch=0.25)

    assert occupancy.shape == (4, 4, 4)
    assert occupancy.all()
    assert origin.shape == (3,)


def test_pair_ray_hit_intervals_pairs_even_hits() -> None:
    intervals = _pair_ray_hit_intervals([0.0, 1.0, 3.0, 4.0])

    assert intervals == [(0.0, 1.0), (3.0, 4.0)]


def test_pair_ray_hit_intervals_uses_wide_fill_for_odd_hits_by_default() -> None:
    intervals = _pair_ray_hit_intervals([0.0, 1.0, 10.0])

    assert intervals == [(0.0, 10.0)]


def test_pair_ray_hit_intervals_can_drop_outlier_for_balanced_odd_hits() -> None:
    intervals = _pair_ray_hit_intervals([0.0, 1.0, 10.0], mode="balanced")

    assert intervals == [(0.0, 1.0)]


def test_voxelize_mesh_supports_ray_voxelizer() -> None:
    output_path = Path("outputs/voxels/test_ray_box_voxels.npz")
    mesh = trimesh.creation.box(extents=(1, 1, 1))
    try:
        voxelize_mesh(mesh, output_path, pitch=0.25, voxelizer="ray", default_color_id=4)

        occupancy, color_ids, _rgb, _origin, _pitch = load_voxel_artifact(output_path)
        assert occupancy.sum() > 0
        assert set(color_ids[occupancy]) == {4}
    finally:
        output_path.unlink(missing_ok=True)


def test_voxelize_mesh_supports_slice_voxelizer() -> None:
    output_path = Path("outputs/voxels/test_slice_box_voxels.npz")
    mesh = trimesh.creation.box(extents=(1, 1, 1))
    try:
        voxelize_mesh(mesh, output_path, pitch=0.25, voxelizer="slice", default_color_id=4)

        occupancy, color_ids, _rgb, _origin, _pitch = load_voxel_artifact(output_path)
        assert occupancy.shape == (4, 4, 4)
        assert occupancy.all()
        assert set(color_ids[occupancy]) == {4}
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


def test_voxelize_mesh_can_sample_vertex_colors_into_voxel_artifact() -> None:
    output_path = Path("outputs/voxels/test_sampled_color_voxels.npz")
    mesh = trimesh.creation.box(extents=(1, 1, 1))
    mesh.visual.vertex_colors = np.tile(
        np.asarray([[242, 205, 55, 255]], dtype=np.uint8),
        (len(mesh.vertices), 1),
    )
    palette_ids, palette_rgb = load_ldraw_palette(Path("data/ldraw/ldraw_colors.json"))

    try:
        artifact = voxelize_mesh(
            mesh,
            output_path,
            pitch=0.5,
            fill=True,
            sample_colors=True,
            palette_ids=palette_ids,
            palette_rgb=palette_rgb,
        )
        occupancy, color_ids, rgb, _origin, _pitch = load_voxel_artifact(artifact.path)

        assert occupancy.any()
        assert np.all(rgb[occupancy] == np.asarray([242, 205, 55], dtype=np.uint8))
        assert np.all(color_ids[occupancy] == 14)
    finally:
        output_path.unlink(missing_ok=True)
