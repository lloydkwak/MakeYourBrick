from __future__ import annotations

import zipfile
from pathlib import Path

from makeyourbrick.studio.analysis import (
    align_cells_to_reference_origin,
    compare_ldr_footprints,
    extract_model_ldr,
    footprint_cells,
    parse_ldr_parts,
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
