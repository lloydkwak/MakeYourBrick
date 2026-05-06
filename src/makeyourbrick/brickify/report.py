from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import numpy as np

from makeyourbrick.types import Brick


def _counter_to_dict(counter: Counter) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(), key=lambda item: str(item[0]))}


def build_brick_report(
    occupancy: np.ndarray,
    input_bricks: list[Brick],
    output_bricks: list[Brick],
    optimized: bool,
) -> dict:
    input_count = len(input_bricks)
    output_count = len(output_bricks)
    reduction_count = input_count - output_count
    reduction_percent = (reduction_count / input_count * 100.0) if input_count else 0.0
    return {
        "optimized": bool(optimized),
        "occupancy_shape": [int(value) for value in occupancy.shape],
        "occupied_voxel_count": int(occupancy.sum()),
        "input_brick_count": int(input_count),
        "output_brick_count": int(output_count),
        "reduction_count": int(reduction_count),
        "reduction_percent": round(float(reduction_percent), 4),
        "part_counts": _counter_to_dict(Counter(brick.part_id for brick in output_bricks)),
        "color_counts": _counter_to_dict(Counter(brick.color_id for brick in output_bricks)),
    }


def write_brick_report(report: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path

