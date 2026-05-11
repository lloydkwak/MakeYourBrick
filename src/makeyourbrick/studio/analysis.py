from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

STUD_LDU = 20
BRICK_HEIGHT_LDU = 24


@dataclass(frozen=True)
class StudioPartFootprint:
    part_id: str
    width: int
    depth: int
    height: int = 1


@dataclass(frozen=True)
class LdrPart:
    color_id: int
    x: float
    y: float
    z: float
    matrix: tuple[float, ...]
    part_id: str


def normalized_part_id(part_id: str) -> str:
    return part_id.strip().lower()


def load_studio_brick_footprints(studio_dir: Path) -> dict[str, StudioPartFootprint]:
    csv_path = studio_dir / "data" / "SplitMerge" / "brick.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Studio brick split/merge catalog not found: {csv_path}")
    footprints: dict[str, StudioPartFootprint] = {}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            part_id = row["LDrawModelName"].strip()
            if not part_id:
                continue
            try:
                length = int(row["X"])
                height = int(row["Y"])
                width = int(row["Z"])
            except (TypeError, ValueError):
                continue
            if height != 1 or width <= 0 or length <= 0:
                continue
            footprints[normalized_part_id(part_id)] = StudioPartFootprint(
                part_id=part_id,
                width=width,
                depth=length,
                height=height,
            )
    return footprints


def extract_model_ldr(io_path: Path, preferred_names: tuple[str, ...] = ("model.ldr", "model2.ldr")) -> str:
    if not zipfile.is_zipfile(io_path):
        return io_path.read_text(encoding="utf-8-sig")
    with zipfile.ZipFile(io_path) as archive:
        names = set(archive.namelist())
        for name in preferred_names:
            if name in names:
                return archive.read(name).decode("utf-8-sig", errors="replace")
        ldr_names = [name for name in archive.namelist() if name.lower().endswith(".ldr")]
        if not ldr_names:
            raise ValueError(f"No LDraw model found inside {io_path}")
        return archive.read(ldr_names[0]).decode("utf-8-sig", errors="replace")


def parse_ldr_parts(text: str) -> list[LdrPart]:
    parts: list[LdrPart] = []
    for line in text.splitlines():
        tokens = line.split()
        if len(tokens) < 15 or tokens[0] != "1":
            continue
        try:
            color_id = int(tokens[1])
            x, y, z = (float(value) for value in tokens[2:5])
            matrix = tuple(float(value) for value in tokens[5:14])
        except ValueError:
            continue
        parts.append(LdrPart(color_id=color_id, x=x, y=y, z=z, matrix=matrix, part_id=tokens[-1]))
    return parts


def is_right_angle_y_rotation(matrix: tuple[float, ...]) -> bool:
    return abs(matrix[2]) > 0.5 or abs(matrix[6]) > 0.5


def part_layer(part: LdrPart) -> int:
    return int(round(-part.y / BRICK_HEIGHT_LDU))


def footprint_cells_for_part(
    part: LdrPart,
    footprints: dict[str, StudioPartFootprint],
) -> set[tuple[int, int, int]]:
    footprint = footprints.get(normalized_part_id(part.part_id))
    if footprint is None:
        return set()
    width = footprint.width
    depth = footprint.depth
    if is_right_angle_y_rotation(part.matrix):
        width, depth = depth, width
    min_x = int(round(part.x / STUD_LDU - (width - 1) / 2))
    min_z = int(round(part.z / STUD_LDU - (depth - 1) / 2))
    layer = part_layer(part)
    return {
        (min_x + dx, layer, min_z + dz)
        for dx in range(width)
        for dz in range(depth)
    }


def footprint_cells(
    parts: Iterable[LdrPart],
    footprints: dict[str, StudioPartFootprint],
) -> set[tuple[int, int, int]]:
    cells: set[tuple[int, int, int]] = set()
    for part in parts:
        cells.update(footprint_cells_for_part(part, footprints))
    return cells


def align_cells_to_reference_origin(
    reference_cells: set[tuple[int, int, int]],
    candidate_cells: set[tuple[int, int, int]],
) -> set[tuple[int, int, int]]:
    if not reference_cells or not candidate_cells:
        return candidate_cells
    ref_min = tuple(min(cell[index] for cell in reference_cells) for index in range(3))
    cand_min = tuple(min(cell[index] for cell in candidate_cells) for index in range(3))
    offset = tuple(ref_min[index] - cand_min[index] for index in range(3))
    return {
        (
            cell[0] + offset[0],
            cell[1] + offset[1],
            cell[2] + offset[2],
        )
        for cell in candidate_cells
    }


def summarize_ldr_parts(
    parts: list[LdrPart],
    footprints: dict[str, StudioPartFootprint] | None = None,
) -> dict:
    if not parts:
        return {
            "brick_count": 0,
            "part_counts": {},
            "layer_count": 0,
            "bounds_ldu": None,
            "footprint_bounds_studs": None,
        }
    xs = [part.x for part in parts]
    ys = [part.y for part in parts]
    zs = [part.z for part in parts]
    summary = {
        "brick_count": len(parts),
        "part_counts": dict(sorted(Counter(part.part_id for part in parts).items())),
        "color_counts": {str(key): int(value) for key, value in sorted(Counter(part.color_id for part in parts).items())},
        "layer_count": len({part_layer(part) for part in parts}),
        "bounds_ldu": {
            "x": [min(xs), max(xs)],
            "y": [min(ys), max(ys)],
            "z": [min(zs), max(zs)],
        },
        "size_studs_from_centers": {
            "x": round((max(xs) - min(xs)) / STUD_LDU, 4),
            "layers": len({part_layer(part) for part in parts}),
            "z": round((max(zs) - min(zs)) / STUD_LDU, 4),
        },
    }
    if footprints is not None:
        cells = footprint_cells(parts, footprints)
        summary["known_footprint_voxel_count"] = len(cells)
        summary["unknown_part_counts"] = dict(
            sorted(Counter(part.part_id for part in parts if normalized_part_id(part.part_id) not in footprints).items())
        )
        if cells:
            cell_x = [cell[0] for cell in cells]
            cell_y = [cell[1] for cell in cells]
            cell_z = [cell[2] for cell in cells]
            summary["footprint_bounds_studs"] = {
                "x": [min(cell_x), max(cell_x) + 1],
                "layers": [min(cell_y), max(cell_y) + 1],
                "z": [min(cell_z), max(cell_z) + 1],
            }
    return summary


def compare_ldr_footprints(
    reference_parts: list[LdrPart],
    candidate_parts: list[LdrPart],
    footprints: dict[str, StudioPartFootprint],
    *,
    align_origin: bool = True,
) -> dict:
    reference_cells = footprint_cells(reference_parts, footprints)
    candidate_cells = footprint_cells(candidate_parts, footprints)
    if align_origin:
        candidate_cells = align_cells_to_reference_origin(reference_cells, candidate_cells)
    shared = reference_cells & candidate_cells
    missing = reference_cells - candidate_cells
    extra = candidate_cells - reference_cells
    union = reference_cells | candidate_cells
    return {
        "reference_voxel_count": len(reference_cells),
        "candidate_voxel_count": len(candidate_cells),
        "shared_voxel_count": len(shared),
        "missing_voxel_count": len(missing),
        "extra_voxel_count": len(extra),
        "iou": round(len(shared) / len(union), 6) if union else 1.0,
        "aligned_origin": bool(align_origin),
        "reference_summary": summarize_ldr_parts(reference_parts, footprints),
        "candidate_summary": summarize_ldr_parts(candidate_parts, footprints),
    }


def write_json(data: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
