from __future__ import annotations

import zipfile
from pathlib import Path

from makeyourbrick.studio.analysis import (
    align_cells_to_reference_origin,
    compare_ldr_footprints,
    extract_model_ldr,
    find_best_xz_alignment,
    footprint_cells,
    parse_ldr_parts,
    summarize_layer_diffs,
    summarize_layer_profiles,
    summarize_profile_deltas,
    summarize_ldr_parts,
)
from makeyourbrick.studio.analysis import StudioPartFootprint


def test_extract_model_ldr_reads_io_zip() -> None:
    io_path = Path("outputs/reports/test_studio_sample.io")
    try:
        io_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io_path, "w") as archive:
            archive.writestr("model.ldr", "0 sample\n1 16 0 0 0 1 0 0 0 1 0 0 0 1 3005.dat\n")

        assert "3005.dat" in extract_model_ldr(io_path)
    finally:
        io_path.unlink(missing_ok=True)


def test_parse_and_summarize_ldr_parts() -> None:
    parts = parse_ldr_parts(
        "0 sample\n"
        "1 16 10 -24 30 1 0 0 0 1 0 0 0 1 3001.dat\n"
        "1 14 0 0 0 1 0 0 0 1 0 0 0 1 3005.dat\n"
    )

    summary = summarize_ldr_parts(parts)

    assert summary["brick_count"] == 2
    assert summary["part_counts"] == {"3001.dat": 1, "3005.dat": 1}
    assert summary["layer_count"] == 2


def test_footprint_cells_uses_studio_part_dimensions_and_rotation() -> None:
    footprints = {
        "3001.dat": StudioPartFootprint("3001.dat", width=2, depth=4),
    }
    parts = parse_ldr_parts("1 16 30 0 10 0 0 1 0 1 0 -1 0 0 3001.dat\n")

    cells = footprint_cells(parts, footprints)

    assert len(cells) == 8
    assert {cell[0] for cell in cells} == {0, 1, 2, 3}
    assert {cell[2] for cell in cells} == {0, 1}


def test_compare_ldr_footprints_reports_iou() -> None:
    footprints = {"3005.dat": StudioPartFootprint("3005.dat", width=1, depth=1)}
    reference = parse_ldr_parts("1 16 0 0 0 1 0 0 0 1 0 0 0 1 3005.dat\n")
    candidate = parse_ldr_parts("1 16 20 0 0 1 0 0 0 1 0 0 0 1 3005.dat\n")

    report = compare_ldr_footprints(reference, candidate, footprints, align_origin=False)

    assert report["iou"] == 0.0
    assert report["missing_voxel_count"] == 1
    assert report["extra_voxel_count"] == 1


def test_compare_ldr_footprints_can_align_origins() -> None:
    footprints = {"3005.dat": StudioPartFootprint("3005.dat", width=1, depth=1)}
    reference = parse_ldr_parts("1 16 0 0 0 1 0 0 0 1 0 0 0 1 3005.dat\n")
    candidate = parse_ldr_parts("1 16 20 -24 20 1 0 0 0 1 0 0 0 1 3005.dat\n")

    report = compare_ldr_footprints(reference, candidate, footprints)

    assert report["iou"] == 1.0
    assert report["aligned_origin"] is True


def test_align_cells_to_reference_origin_translates_candidate_minimum() -> None:
    reference = {(10, 2, -4)}
    candidate = {(1, 1, 1), (2, 1, 1)}

    aligned = align_cells_to_reference_origin(reference, candidate)

    assert (10, 2, -4) in aligned
    assert (11, 2, -4) in aligned


def test_summarize_layer_diffs_reports_per_layer_mismatch() -> None:
    reference = {(0, 0, 0), (1, 0, 0), (0, 1, 0)}
    candidate = {(0, 0, 0), (2, 0, 0), (0, 2, 0)}

    diffs = summarize_layer_diffs(reference, candidate)

    assert [diff["layer"] for diff in diffs] == [0, 1, 2]
    assert diffs[0]["shared_voxels"] == 1
    assert diffs[0]["missing_voxels"] == 1
    assert diffs[0]["extra_voxels"] == 1
    assert diffs[1]["candidate_voxels"] == 0
    assert diffs[2]["reference_voxels"] == 0


def test_compare_ldr_footprints_includes_layer_diagnostics() -> None:
    footprints = {"3005.dat": StudioPartFootprint("3005.dat", width=1, depth=1)}
    reference = parse_ldr_parts(
        "1 16 0 0 0 1 0 0 0 1 0 0 0 1 3005.dat\n"
        "1 16 0 -24 0 1 0 0 0 1 0 0 0 1 3005.dat\n"
    )
    candidate = parse_ldr_parts("1 16 20 0 0 1 0 0 0 1 0 0 0 1 3005.dat\n")

    report = compare_ldr_footprints(reference, candidate, footprints, align_origin=False)

    assert report["layer_diffs"][0]["layer"] == 0
    assert report["worst_missing_layers"][0]["missing_voxels"] == 1
    assert report["worst_extra_layers"][0]["extra_voxels"] == 1


def test_find_best_xz_alignment_handles_rotated_candidate() -> None:
    reference = {(0, 0, 0), (1, 0, 0), (2, 0, 0)}
    candidate = {(0, 0, 0), (0, 0, 1), (0, 0, 2)}

    aligned, report = find_best_xz_alignment(reference, candidate)

    assert aligned == reference
    assert report["transform"] in {"rotate_90", "rotate_270", "mirror_diagonal", "mirror_antidiagonal"}
    assert report["iou"] == 1.0


def test_summarize_layer_profiles_reports_area_and_bounds_curves() -> None:
    reference = {(0, 0, 0), (1, 0, 0), (0, 1, 0)}
    candidate = {(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0), (1, 1, 0)}

    profiles = summarize_layer_profiles(reference, candidate)

    assert profiles[0]["layer"] == 0
    assert profiles[0]["reference_area"] == 2
    assert profiles[0]["candidate_area"] == 3
    assert profiles[0]["area_delta"] == 1
    assert profiles[0]["reference_width"] == 2
    assert profiles[0]["candidate_width"] == 3
    assert profiles[1]["area_ratio"] == 2.0


def test_summarize_profile_deltas_reports_global_size_ratios() -> None:
    reference = {(0, 0, 0), (1, 0, 0), (0, 1, 0)}
    candidate = {(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 1, 0), (1, 1, 0)}
    profiles = summarize_layer_profiles(reference, candidate)

    summary = summarize_profile_deltas(reference, candidate, profiles)

    assert summary["total_area_delta"] == 2
    assert summary["total_area_ratio"] == 1.666667
    assert summary["global_width_ratio"] == 1.5
    assert summary["global_depth_ratio"] == 1.0
    assert summary["global_layer_ratio"] == 1.0
