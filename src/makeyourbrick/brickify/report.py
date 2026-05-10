from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

from makeyourbrick.types import Brick
from makeyourbrick.brickify.optimizer import bricks_to_occupancy, seam_overlap_ratio, support_ratio_for_area


def _counter_to_dict(counter: Counter) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda item: str(item[0]))}


def build_brick_report(
    occupancy: np.ndarray,
    input_bricks: list[Brick],
    output_bricks: list[Brick],
    optimized: bool,
    optimizer: str = "greedy",
    stability: dict | None = None,
    sculpture: dict | None = None,
) -> dict:
    input_count = len(input_bricks)
    output_count = len(output_bricks)
    reduction_count = input_count - output_count
    reduction_percent = (reduction_count / input_count * 100.0) if input_count else 0.0
    report = {
        "optimized": bool(optimized),
        "optimizer": optimizer,
        "occupancy_shape": [int(value) for value in occupancy.shape],
        "occupied_voxel_count": int(occupancy.sum()),
        "input_brick_count": int(input_count),
        "output_brick_count": int(output_count),
        "reduction_count": int(reduction_count),
        "reduction_percent": round(float(reduction_percent), 4),
        "part_counts": _counter_to_dict(Counter(brick.part_id for brick in output_bricks)),
        "color_counts": _counter_to_dict(Counter(brick.color_id for brick in output_bricks)),
    }
    if sculpture is not None:
        report["sculpture"] = sculpture
    if stability is not None:
        report["stability"] = stability
    return report


def build_stability_report(
    bricks: list[Brick],
    occupancy_shape: tuple[int, int, int],
    *,
    sculpture_mode: str = "solid",
    wall_thickness: int = 1,
    base_thickness: int = 0,
) -> dict:
    if not bricks:
        return {
            "unsupported_brick_count": 0,
            "floating_brick_count": 0,
            "average_support_ratio": 1.0,
            "vertical_seam_alignment_score": 0.0,
            "layer_count": 0,
            "sculpture_mode": sculpture_mode,
            "wall_thickness": int(wall_thickness),
            "base_thickness": int(base_thickness),
        }
    brick_occupancy = bricks_to_occupancy(bricks, occupancy_shape)
    support_ratios = [
        support_ratio_for_area(brick_occupancy, brick.x, brick.y, brick.z, brick.width, brick.depth)
        for brick in bricks
    ]
    seam_scores = [
        seam_overlap_ratio(bricks, brick.y, brick.x, brick.z, brick.width, brick.depth)
        for brick in bricks
        if brick.y > 0
    ]
    unsupported = sum(1 for brick, ratio in zip(bricks, support_ratios) if brick.y > 0 and ratio < 1.0)
    floating = sum(1 for brick, ratio in zip(bricks, support_ratios) if brick.y > 0 and ratio == 0.0)
    return {
        "unsupported_brick_count": int(unsupported),
        "floating_brick_count": int(floating),
        "average_support_ratio": round(float(np.mean(support_ratios)), 4),
        "vertical_seam_alignment_score": round(float(np.mean(seam_scores)) if seam_scores else 0.0, 4),
        "layer_count": int(len({brick.y for brick in bricks})),
        "sculpture_mode": sculpture_mode,
        "wall_thickness": int(wall_thickness),
        "base_thickness": int(base_thickness),
    }


def write_brick_report(report: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
