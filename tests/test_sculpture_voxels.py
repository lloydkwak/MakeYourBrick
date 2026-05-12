from __future__ import annotations

import numpy as np
import pytest

from makeyourbrick.voxel.sculpture import (
    anchor_shell_to_base,
    add_vertical_support_columns,
    apply_sculpture_mode,
    apply_voxel_smoothing,
    contour_shell_mask,
    dilate_layer_within,
    fill_2d_holes,
    fill_horizontal_layer_holes,
    fill_vertical_layer_gaps,
    lattice_infill_mask,
    lattice_spacing_for_density,
    layer_neighbor_count_8,
    layer_surface_mask,
    remove_small_layer_components,
    rib_infill_mask,
    smooth_2d_contour,
    smooth_2d_polished_contour,
    smooth_polished_layers,
    smooth_profile_layers,
    smooth_studio_layers,
    trim_layer_to_neighbor_profile,
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


def test_layer_surface_mask_detects_2d_contour() -> None:
    layer = np.ones((5, 5), dtype=bool)

    surface = layer_surface_mask(layer)

    assert surface.sum() == 16
    assert not surface[2, 2]


def test_contour_shell_mask_keeps_layer_walls_not_interior() -> None:
    occupancy = np.ones((5, 3, 5), dtype=bool)

    shell = contour_shell_mask(occupancy, wall_thickness=1)

    assert shell[:, 0, :].sum() == 16
    assert not shell[2, 1, 2]
    assert shell[0, 1, 0]


def test_contour_shell_mode_keeps_base_layers_solid() -> None:
    occupancy = np.ones((5, 4, 5), dtype=bool)
    color_ids = np.full(occupancy.shape, 16, dtype=np.int32)

    shell, shell_colors = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode="contour-shell",
        wall_thickness=1,
        base_thickness=1,
    )

    assert shell[:, 0, :].all()
    assert not shell[2, 2, 2]
    assert shell_colors[shell].min() == 16


def test_add_vertical_support_columns_fills_only_needed_columns() -> None:
    occupancy = np.ones((4, 4, 4), dtype=bool)
    shell = np.zeros_like(occupancy)
    shell[2, 3, 2] = True
    shell[0, 0, 0] = True

    supported = add_vertical_support_columns(shell, occupancy, base_thickness=1)

    assert supported[2, 0:4, 2].all()
    assert supported[0, 0, 0]
    assert not supported[1, 1, 1]


def test_add_vertical_support_columns_can_use_sparse_spacing() -> None:
    occupancy = np.ones((5, 4, 5), dtype=bool)
    shell = np.zeros_like(occupancy)
    shell[1, 3, 1] = True
    shell[2, 3, 1] = True

    supported = add_vertical_support_columns(shell, occupancy, support_spacing=3)

    assert supported.sum() < add_vertical_support_columns(shell, occupancy, support_spacing=1).sum()


def test_contour_shell_mode_adds_minimal_vertical_support_columns() -> None:
    occupancy = np.zeros((4, 4, 4), dtype=bool)
    occupancy[:, 0, :] = True
    occupancy[1, 1, 1] = True
    occupancy[2, 1, 1] = True
    occupancy[2, 2, 1] = True
    occupancy[2, 3, 1] = True
    color_ids = np.full(occupancy.shape, 16, dtype=np.int32)

    shell, _colors = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode="contour-shell",
        wall_thickness=1,
        base_thickness=1,
    )

    assert shell[:, 0, :].all()
    assert shell[2, 1:4, 1].all()


def test_dilate_layer_within_respects_layer_limit() -> None:
    seed = np.zeros((5, 5), dtype=bool)
    seed[0, 2] = True
    limit = np.zeros((5, 5), dtype=bool)
    limit[0:3, 2] = True

    dilated = dilate_layer_within(seed, limit, iterations=4)

    assert dilated[2, 2]
    assert not dilated[3, 2]


def test_density_mode_keeps_shell_base_and_lattice_infill() -> None:
    occupancy = np.ones((7, 5, 7), dtype=bool)
    color_ids = np.full(occupancy.shape, 16, dtype=np.int32)

    density, density_colors = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode="density",
        wall_thickness=1,
        base_thickness=1,
        infill_density=0.35,
    )
    shell, _shell_colors = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode="shell",
        wall_thickness=1,
        base_thickness=1,
    )

    assert shell.sum() < density.sum() < occupancy.sum()
    assert density[:, 0, :].all()
    assert density[0, 2, 0]
    assert not density[2, 2, 2]
    assert density_colors[density].min() == 16


def test_density_mode_can_use_rib_support_infill() -> None:
    occupancy = np.ones((8, 4, 8), dtype=bool)
    color_ids = np.full(occupancy.shape, 16, dtype=np.int32)

    density, _colors = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode="density",
        wall_thickness=1,
        base_thickness=1,
        infill_density=0.35,
        infill_pattern="ribs",
    )

    assert density[:, 0, :].all()
    assert density[0, 2, 0]
    assert density[2, 2, 0]
    assert density[0, 2, 4]
    assert not density[3, 2, 3]


def test_lattice_infill_density_bounds() -> None:
    occupancy = np.ones((8, 1, 8), dtype=bool)

    assert lattice_spacing_for_density(0.0) == 0
    assert lattice_spacing_for_density(1.0) == 1
    assert not lattice_infill_mask(occupancy, 0.0).any()
    assert lattice_infill_mask(occupancy, 1.0).all()
    assert 0 < lattice_infill_mask(occupancy, 0.35).sum() < occupancy.sum()


def test_rib_infill_staggers_support_lines_by_layer() -> None:
    occupancy = np.ones((8, 4, 8), dtype=bool)

    ribs = rib_infill_mask(occupancy, 0.35)

    assert ribs[0, 0, 0]
    assert ribs[5, 0, 0]
    assert ribs[1, 1, 0]
    assert not ribs[1, 0, 1]
    assert 0 < ribs.sum() < occupancy.sum()


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


def test_light_voxel_smoothing_removes_unsupported_layer_spurs() -> None:
    occupancy = np.zeros((5, 1, 5), dtype=bool)
    occupancy[1:4, 0, 2] = True
    occupancy[4, 0, 2] = True

    smoothed = apply_voxel_smoothing(occupancy, "light")

    assert smoothed[2, 0, 2]
    assert not smoothed[4, 0, 2]


def test_light_voxel_smoothing_preserves_vertically_supported_tips() -> None:
    occupancy = np.zeros((3, 2, 3), dtype=bool)
    occupancy[1, :, 1] = True

    smoothed = apply_voxel_smoothing(occupancy, "light")

    assert smoothed[1, 0, 1]
    assert smoothed[1, 1, 1]


def test_smooth_2d_contour_fills_corners_and_removes_spurs() -> None:
    layer = np.zeros((5, 5), dtype=bool)
    layer[1:4, 1:4] = True
    layer[2, 2] = False
    layer[4, 2] = True

    smoothed = smooth_2d_contour(layer)

    assert smoothed[2, 2]
    assert not smoothed[4, 2]


def test_eight_neighbor_count_includes_diagonals() -> None:
    layer = np.zeros((3, 3), dtype=bool)
    layer[0, 0] = True
    layer[0, 1] = True

    counts = layer_neighbor_count_8(layer)

    assert counts[1, 1] == 2


def test_smooth_2d_polished_contour_removes_noise_and_fills_cavities() -> None:
    layer = np.zeros((7, 7), dtype=bool)
    layer[1:6, 1:6] = True
    layer[3, 3] = False
    layer[6, 6] = True

    smoothed = smooth_2d_polished_contour(layer)

    assert smoothed[3, 3]
    assert not smoothed[6, 6]


def test_contour_voxel_smoothing_applies_layer_cleanup() -> None:
    occupancy = np.zeros((5, 1, 5), dtype=bool)
    occupancy[1:4, 0, 1:4] = True
    occupancy[2, 0, 2] = False
    occupancy[4, 0, 2] = True

    smoothed = apply_voxel_smoothing(occupancy, "contour")

    assert smoothed[2, 0, 2]
    assert not smoothed[4, 0, 2]


def test_fill_vertical_layer_gaps_fills_missing_middle_voxels() -> None:
    occupancy = np.zeros((3, 3, 3), dtype=bool)
    occupancy[1, 0, 1] = True
    occupancy[1, 2, 1] = True

    filled = fill_vertical_layer_gaps(occupancy)

    assert filled[1, 1, 1]


def test_studio_voxel_smoothing_fills_layer_holes_and_vertical_gaps() -> None:
    occupancy = np.zeros((5, 3, 5), dtype=bool)
    occupancy[1:4, 0, 1:4] = True
    occupancy[2, 0, 2] = False
    occupancy[1:4, 2, 1:4] = True
    occupancy[4, 1, 4] = True

    smoothed = smooth_studio_layers(occupancy)

    assert smoothed[2, 0, 2]
    assert smoothed[2, 1, 2]
    assert not smoothed[4, 1, 4]


def test_studio_voxel_smoothing_preset_is_available() -> None:
    occupancy = np.zeros((3, 3, 3), dtype=bool)
    occupancy[1, 0, 1] = True
    occupancy[1, 2, 1] = True

    smoothed = apply_voxel_smoothing(occupancy, "studio")

    assert smoothed[1, 1, 1]


def test_remove_small_layer_components_drops_isolated_islands() -> None:
    layer = np.zeros((8, 8), dtype=bool)
    layer[1:5, 1:5] = True
    layer[7, 7] = True

    cleaned = remove_small_layer_components(layer)

    assert cleaned[2, 2]
    assert not cleaned[7, 7]


def test_trim_layer_to_neighbor_profile_limits_outside_spikes() -> None:
    layer = np.zeros((8, 8), dtype=bool)
    layer[2:5, 2:5] = True
    layer[7, 7] = True
    neighbor_profile = np.zeros((8, 8), dtype=bool)
    neighbor_profile[2:5, 2:5] = True

    trimmed = trim_layer_to_neighbor_profile(layer, neighbor_profile)

    assert trimmed[3, 3]
    assert not trimmed[7, 7]


def test_profile_voxel_smoothing_removes_layer_islands_and_keeps_body() -> None:
    occupancy = np.zeros((8, 3, 8), dtype=bool)
    occupancy[2:6, :, 2:6] = True
    occupancy[7, 1, 7] = True
    occupancy[3, 1, 3] = False

    smoothed = smooth_profile_layers(occupancy)

    assert smoothed[3, 1, 3]
    assert smoothed[4, 1, 4]
    assert not smoothed[7, 1, 7]


def test_profile_voxel_smoothing_preset_is_available() -> None:
    occupancy = np.zeros((5, 3, 5), dtype=bool)
    occupancy[1:4, :, 1:4] = True
    occupancy[4, 1, 4] = True

    smoothed = apply_voxel_smoothing(occupancy, "profile")

    assert smoothed[2, 1, 2]
    assert not smoothed[4, 1, 4]


def test_polished_voxel_smoothing_reduces_jagged_layer_noise() -> None:
    occupancy = np.zeros((7, 3, 7), dtype=bool)
    occupancy[1:6, :, 1:6] = True
    occupancy[3, 1, 3] = False
    occupancy[6, 1, 6] = True

    smoothed = smooth_polished_layers(occupancy)

    assert smoothed[3, 1, 3]
    assert smoothed[4, 1, 4]
    assert not smoothed[6, 1, 6]


def test_polished_voxel_smoothing_preset_is_available() -> None:
    occupancy = np.zeros((5, 3, 5), dtype=bool)
    occupancy[1:4, :, 1:4] = True
    occupancy[4, 1, 4] = True

    smoothed = apply_voxel_smoothing(occupancy, "polished")

    assert smoothed[2, 1, 2]
    assert not smoothed[4, 1, 4]


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

    with pytest.raises(ValueError, match="smoothing"):
        apply_sculpture_mode(occupancy, color_ids, voxel_smoothing="heavy")

    with pytest.raises(ValueError, match="infill_density"):
        apply_sculpture_mode(occupancy, color_ids, mode="density", infill_density=1.5)

    with pytest.raises(ValueError, match="infill pattern"):
        apply_sculpture_mode(occupancy, color_ids, mode="density", infill_pattern="random")
