from __future__ import annotations

import json
from pathlib import Path

from makeyourbrick.brickify.optimizer import brickify_1x1, greedy_brickify
from makeyourbrick.brickify.report import build_brick_report, write_brick_report
from makeyourbrick.voxel.synthetic import make_solid_box


def test_build_brick_report_summarizes_reduction_and_counts() -> None:
    occupancy, color_ids = make_solid_box((4, 1, 2), color_id=16)
    input_bricks = brickify_1x1(occupancy, color_ids)
    output_bricks = greedy_brickify(occupancy, color_ids)

    report = build_brick_report(occupancy, input_bricks, output_bricks, optimized=True)

    assert report["optimized"] is True
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

