from __future__ import annotations

import json
from pathlib import Path

from makeyourbrick.brickify.optimizer import brickify_1x1, greedy_brickify
from makeyourbrick.brickify.report import build_brick_report, build_stability_report, write_brick_report
from makeyourbrick.types import Brick
from makeyourbrick.voxel.synthetic import make_solid_box


def test_build_brick_report_summarizes_reduction_and_counts() -> None:
    occupancy, color_ids = make_solid_box((4, 1, 2), color_id=16)
    input_bricks = brickify_1x1(occupancy, color_ids)
    output_bricks = greedy_brickify(occupancy, color_ids)

    report = build_brick_report(occupancy, input_bricks, output_bricks, optimized=True)

    assert report["optimized"] is True
    assert report["optimizer"] == "greedy"
    assert report["occupancy_shape"] == [4, 1, 2]
    assert report["occupied_voxel_count"] == 8
    assert report["input_brick_count"] == 8
    assert report["output_brick_count"] == 1
    assert report["reduction_count"] == 7
    assert report["reduction_percent"] == 87.5
    assert report["part_counts"] == {"3001.dat": 1}
    assert report["color_counts"] == {"16": 1}


def test_write_brick_report_writes_json() -> None:
    output_path = Path("outputs/reports/test_brick_report.json")
    try:
        write_brick_report({"output_brick_count": 1}, output_path)

        assert json.loads(output_path.read_text(encoding="utf-8")) == {"output_brick_count": 1}
    finally:
        output_path.unlink(missing_ok=True)


def test_build_stability_report_counts_support_and_layers() -> None:
    bricks = [
        Brick("3005.dat", 16, 0, 0, 0, 1, 1),
        Brick("3005.dat", 16, 0, 1, 0, 1, 1),
        Brick("3005.dat", 16, 2, 1, 0, 1, 1),
    ]

    report = build_stability_report(
        bricks,
        (3, 2, 1),
        sculpture_mode="shell",
        wall_thickness=1,
        base_thickness=1,
    )

    assert report["unsupported_brick_count"] == 1
    assert report["floating_brick_count"] == 1
    assert report["layer_count"] == 2
    assert report["sculpture_mode"] == "shell"


def test_build_brick_report_can_include_sculpture_and_stability_sections() -> None:
    occupancy, color_ids = make_solid_box((1, 1, 1), color_id=16)
    bricks = brickify_1x1(occupancy, color_ids)

    report = build_brick_report(
        occupancy,
        bricks,
        bricks,
        optimized=False,
        optimizer="none",
        sculpture={"mode": "solid"},
        stability={"layer_count": 1},
    )

    assert report["sculpture"] == {"mode": "solid"}
    assert report["stability"] == {"layer_count": 1}
