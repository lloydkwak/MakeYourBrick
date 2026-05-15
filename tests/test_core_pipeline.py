from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

from makeyourbrick.brickify.optimizer import bricks_to_occupancy
from makeyourbrick.sculpture import (
    SculptureSettings,
    VoxelModel,
    build_contour_shell_targets,
    build_filled_layer_targets,
    catalog_for_palette,
    layered_model_matches_target,
    place_layered_bricks,
)

trimesh = pytest.importorskip("trimesh")


def _brick_footprint(part_id: str) -> tuple[int, int]:
    return {
        "3008.dat": (1, 8),
        "3007.dat": (2, 8),
        "3009.dat": (1, 6),
        "2456.dat": (2, 6),
        "3010.dat": (1, 4),
        "3001.dat": (2, 4),
        "3622.dat": (1, 3),
        "3002.dat": (2, 3),
        "3004.dat": (1, 2),
        "3003.dat": (2, 2),
        "3005.dat": (1, 1),
    }[part_id]


def test_studio_layered_placement_exactly_covers_base_and_shell() -> None:
    occupancy = np.ones((8, 5, 8), dtype=bool)
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
    assert any(brick.part_id == "3007.dat" for brick in model.bricks_by_layer[0])
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
            "--output",
            str(ldr_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    brick_lines = [line for line in ldr_path.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
    parts = Counter(line.split()[-1] for line in brick_lines)
    colors = {line.split()[1] for line in brick_lines}

    assert voxel_path.exists()
    assert report["optimizer"] == "studio-layered"
    assert report["brick_palette"] == "studio"
    assert report["sculpture"]["wall_thickness"] == 2
    assert report["sculpture"]["base_thickness"] == 3
    assert report["sculpture"]["mode"] == "filled-layer"
    assert report["exact_cover"] is True
    assert report["missed_voxel_count"] == 0
    assert report["overflow_voxel_count"] == 0
    assert report["output_brick_count"] == len(brick_lines)
    assert colors <= {"1", "2", "3", "13", "15", "19", "20", "27"}
    assert "3007.dat" in parts or "3008.dat" in parts
    assert "0 STEP" in ldr_path.read_text(encoding="utf-8")


def test_ldr_part_dimensions_are_known_for_core_palette() -> None:
    assert _brick_footprint("3007.dat") == (2, 8)
    assert _brick_footprint("3005.dat") == (1, 1)
