from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from makeyourbrick.brickify.optimizer import bricks_to_occupancy
from makeyourbrick.brickify.report import build_stability_report
from makeyourbrick.io.ldr_writer import brick_to_ldr_line
from makeyourbrick.pipeline import convert_mesh_to_ldr
from makeyourbrick.sculpture import (
    SculptureSettings,
    VoxelModel,
    build_contour_shell_targets,
    build_filled_layer_targets,
    catalog_for_palette,
    layered_model_matches_target,
    place_layered_bricks,
)
from makeyourbrick.types import Brick

trimesh = pytest.importorskip("trimesh")


def _brick_footprint(part_id: str) -> tuple[int, int]:
    return {
        "3008.dat": (8, 1),
        "3007.dat": (8, 2),
        "3009.dat": (6, 1),
        "2456.dat": (6, 2),
        "3010.dat": (4, 1),
        "3001.dat": (4, 2),
        "3622.dat": (3, 1),
        "3002.dat": (3, 2),
        "3004.dat": (2, 1),
        "3003.dat": (2, 2),
        "3005.dat": (1, 1),
    }[part_id]


def test_studio_layered_placement_exactly_covers_base_and_shell() -> None:
    occupancy = np.ones((8, 8, 8), dtype=bool)
    colors = np.where(occupancy, 16, 0).astype(np.int32)
    solid = VoxelModel(occupancy, colors, pitch=1.0, origin=(0.0, 0.0, 0.0))
    target = build_contour_shell_targets(
        solid,
        SculptureSettings(wall_thickness=2, base_thickness=3),
    ).target

    model = place_layered_bricks(target, catalog_for_palette("studio"))

    assert layered_model_matches_target(model, target)
    assert target.occupancy[:, 0, :].all()
    assert target.occupancy[:, 1, :].all()
    assert target.occupancy[:, 2, :].all()
    assert not target.occupancy[3, 4, 3]
    assert {brick.color_id for brick in model.bricks_by_layer[0]} == {15}
    assert model.bricks_by_layer[0]
    assert np.array_equal(bricks_to_occupancy(model.bricks(), target.shape), target.occupancy)


def test_filled_layer_target_keeps_the_complete_mesh_footprint() -> None:
    occupancy = np.ones((8, 5, 8), dtype=bool)
    occupancy[3:5, 3:, 3:5] = False
    colors = np.where(occupancy, 16, 0).astype(np.int32)
    solid = VoxelModel(occupancy, colors, pitch=1.0, origin=(0.0, 0.0, 0.0))
    targets = build_filled_layer_targets(
        solid,
        SculptureSettings(wall_thickness=2, base_thickness=3),
    )

    assert np.array_equal(targets.target.occupancy, occupancy)
    assert targets.shell.occupancy.sum() < targets.target.occupancy.sum()


def test_mesh_to_ldr_cli_writes_studio_sculpture(tmp_path: Path) -> None:
    mesh_path = tmp_path / "box.obj"
    voxel_path = tmp_path / "box.npz"
    ldr_path = tmp_path / "box.ldr"
    debug_target_path = tmp_path / "box_target_1x1.ldr"
    report_path = tmp_path / "box_report.json"
    trimesh.creation.box(extents=(1.0, 2.0, 1.0)).export(mesh_path)

    subprocess.run(
        [
            sys.executable,
            "scripts/mesh_to_ldr.py",
            "--mesh",
            str(mesh_path),
            "--base-size-studs",
            "8",
            "--wall-thickness",
            "2",
            "--base-thickness",
            "3",
            "--voxels",
            str(voxel_path),
            "--report",
            str(report_path),
            "--debug-target-output",
            str(debug_target_path),
            "--output",
            str(ldr_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    brick_lines = [line for line in ldr_path.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
    debug_lines = [line for line in debug_target_path.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
    parts = Counter(line.split()[-1] for line in brick_lines)
    colors = {line.split()[1] for line in brick_lines}

    assert voxel_path.exists()
    assert debug_target_path.exists()
    assert report["optimizer"] == "studio-layered"
    assert report["brick_palette"] == "studio"
    assert report["sculpture"]["wall_thickness"] == 2
    assert report["sculpture"]["base_thickness"] == 3
    assert report["sculpture"]["mode"] == "contour-shell"
    assert report["sculpture"]["voxelizer"] in {"slice", "surface"}
    assert report["exact_cover"] is True
    assert report["missed_voxel_count"] == 0
    assert report["overflow_voxel_count"] == 0
    assert report["output_brick_count"] == len(brick_lines)
    assert report["input_brick_count"] == len(debug_lines)
    assert {line.split()[-1] for line in debug_lines} == {"3005.dat"}
    assert colors <= {"1", "2", "3", "13", "15", "19", "20", "27"}
    assert set(parts) <= {
        "3008.dat",
        "3007.dat",
        "3009.dat",
        "2456.dat",
        "3010.dat",
        "3001.dat",
        "3622.dat",
        "3002.dat",
        "3004.dat",
        "3003.dat",
        "3005.dat",
    }
    assert "0 STEP" in ldr_path.read_text(encoding="utf-8")


def test_ldr_part_dimensions_are_known_for_core_palette() -> None:
    assert _brick_footprint("3007.dat") == (8, 2)
    assert _brick_footprint("3005.dat") == (1, 1)


def test_ldraw_writer_uses_ldraw_default_part_axes() -> None:
    horizontal = Brick(part_id="3010.dat", color_id=16, x=0, y=0, z=0, width=4, depth=1)
    vertical = Brick(part_id="3010.dat", color_id=16, x=0, y=0, z=0, width=1, depth=4, rotation_degrees=90)

    assert "30 0 0 1 0 0 0 1 0 0 0 1 3010.dat" in brick_to_ldr_line(horizontal)
    assert "0 0 30 0 0 -1 0 1 0 1 0 0 3010.dat" in brick_to_ldr_line(vertical)


def test_stability_report_counts_top_attached_bricks() -> None:
    lower = Brick(part_id="3005.dat", color_id=16, x=0, y=0, z=0, width=1, depth=1)
    middle = Brick(part_id="3005.dat", color_id=16, x=1, y=1, z=0, width=1, depth=1)
    upper = Brick(part_id="3004.dat", color_id=16, x=0, y=2, z=0, width=2, depth=1)

    report = build_stability_report([lower, middle, upper], (2, 3, 1))

    assert report["floating_brick_count"] == 1
    assert report["top_attached_only_brick_count"] == 1
    assert report["bidirectional_unattached_brick_count"] == 0


def test_auto_base_size_records_selected_size(tmp_path: Path) -> None:
    mesh_path = tmp_path / "wide.obj"
    voxel_path = tmp_path / "wide.npz"
    ldr_path = tmp_path / "wide.ldr"
    report_path = tmp_path / "wide_report.json"
    trimesh.creation.box(extents=(8.0, 1.0, 2.0)).export(mesh_path)

    convert_mesh_to_ldr(
        mesh_path=mesh_path,
        ldr_output_path=ldr_path,
        voxel_output_path=voxel_path,
        report_path=report_path,
        base_size_studs="auto",
        up_axis="y",
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["footprint_scale"]["requested_base_size_studs"] == "auto"
    assert report["footprint_scale"]["base_size_studs"] in {16, 24, 32, 48, 64}
