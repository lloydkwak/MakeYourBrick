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
    mesh_orientation: dict | None = None,
    footprint_scale: dict | None = None,
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
    if mesh_orientation is not None:
        report["mesh_orientation"] = mesh_orientation
    if footprint_scale is not None:
        report["footprint_scale"] = footprint_scale
    if stability is not None:
        report["stability"] = stability
    return report


def connected_component_sizes(occupancy: np.ndarray) -> list[int]:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    visited = np.zeros_like(occupancy, dtype=bool)
    sizes: list[int] = []
    width, height, depth = occupancy.shape
    for start in np.argwhere(occupancy):
        x, y, z = (int(value) for value in start)
        if visited[x, y, z]:
            continue
        stack = [(x, y, z)]
        visited[x, y, z] = True
        size = 0
        while stack:
            cx, cy, cz = stack.pop()
            size += 1
            for dx, dy, dz in (
                (-1, 0, 0),
                (1, 0, 0),
                (0, -1, 0),
                (0, 1, 0),
                (0, 0, -1),
                (0, 0, 1),
            ):
                nx, ny, nz = cx + dx, cy + dy, cz + dz
                if not (0 <= nx < width and 0 <= ny < height and 0 <= nz < depth):
                    continue
                if occupancy[nx, ny, nz] and not visited[nx, ny, nz]:
                    visited[nx, ny, nz] = True
                    stack.append((nx, ny, nz))
        sizes.append(size)
    return sorted(sizes, reverse=True)


def build_stability_report(
    bricks: list[Brick],
    occupancy_shape: tuple[int, int, int],
    *,
    sculpture_mode: str = "solid",
    wall_thickness: int = 1,
    base_thickness: int = 0,
    low_support_threshold: float = 0.5,
    overhang_risk_threshold: float = 0.75,
) -> dict:
    if not bricks:
        return {
            "unsupported_brick_count": 0,
            "floating_brick_count": 0,
            "low_support_brick_count": 0,
            "overhang_risk_brick_count": 0,
            "average_support_ratio": 1.0,
            "vertical_seam_alignment_score": 0.0,
            "connected_component_count": 0,
            "largest_connected_component_voxel_count": 0,
            "disconnected_voxel_count": 0,
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
    low_support = sum(
        1 for brick, ratio in zip(bricks, support_ratios) if brick.y > 0 and 0.0 < ratio < low_support_threshold
    )
    overhang_risk = sum(
        1
        for brick, ratio in zip(bricks, support_ratios)
        if brick.y > 0 and 0.0 < ratio < overhang_risk_threshold
    )
    component_sizes = connected_component_sizes(brick_occupancy)
    largest_component = component_sizes[0] if component_sizes else 0
    return {
        "unsupported_brick_count": int(unsupported),
        "floating_brick_count": int(floating),
        "low_support_brick_count": int(low_support),
        "overhang_risk_brick_count": int(overhang_risk),
        "average_support_ratio": round(float(np.mean(support_ratios)), 4),
        "vertical_seam_alignment_score": round(float(np.mean(seam_scores)) if seam_scores else 0.0, 4),
        "connected_component_count": int(len(component_sizes)),
        "largest_connected_component_voxel_count": int(largest_component),
        "disconnected_voxel_count": int(max(0, brick_occupancy.sum() - largest_component)),
        "layer_count": int(len({brick.y for brick in bricks})),
        "sculpture_mode": sculpture_mode,
        "wall_thickness": int(wall_thickness),
        "base_thickness": int(base_thickness),
    }


def write_brick_report(report: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
