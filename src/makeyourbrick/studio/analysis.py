from __future__ import annotations

import csv
import json
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

STUD_LDU = 20
BRICK_HEIGHT_LDU = 24
BRICK_FOOTPRINTS = {
    "3006.dat": (2, 10),
    "3007.dat": (2, 8),
    "2456.dat": (2, 6),
    "3001.dat": (2, 4),
    "3008.dat": (1, 8),
    "3002.dat": (2, 3),
    "3009.dat": (1, 6),
    "3010.dat": (1, 4),
    "3003.dat": (2, 2),
    "3622.dat": (1, 3),
    "3004.dat": (1, 2),
    "3005.dat": (1, 1),
}
PLATE_FOOTPRINTS = {
    "3020.dat": (2, 4),
    "3710.dat": (1, 4),
    "3021.dat": (2, 3),
    "3022.dat": (2, 2),
    "3023.dat": (1, 2),
    "3024.dat": (1, 1),
}


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
    for part_id, (width, depth) in {**BRICK_FOOTPRINTS, **PLATE_FOOTPRINTS}.items():
        footprints.setdefault(
            normalized_part_id(part_id),
            StudioPartFootprint(part_id=part_id, width=width, depth=depth, height=1),
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
    aligned, _ = align_cells_to_reference_origin_with_offset(reference_cells, candidate_cells)
    return aligned


def align_cells_to_reference_origin_with_offset(
    reference_cells: set[tuple[int, int, int]],
    candidate_cells: set[tuple[int, int, int]],
) -> tuple[set[tuple[int, int, int]], tuple[int, int, int]]:
    if not reference_cells or not candidate_cells:
        return candidate_cells, (0, 0, 0)
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
    }, offset


def cell_bounds(cells: set[tuple[int, int, int]]) -> dict[str, list[int]] | None:
    if not cells:
        return None
    return {
        "x": [min(cell[0] for cell in cells), max(cell[0] for cell in cells) + 1],
        "layers": [min(cell[1] for cell in cells), max(cell[1] for cell in cells) + 1],
        "z": [min(cell[2] for cell in cells), max(cell[2] for cell in cells) + 1],
    }


def xz_bounds(cells: set[tuple[int, int, int]]) -> dict[str, list[int]] | None:
    if not cells:
        return None
    return {
        "x": [min(cell[0] for cell in cells), max(cell[0] for cell in cells) + 1],
        "z": [min(cell[2] for cell in cells), max(cell[2] for cell in cells) + 1],
    }


def bounds_size(bounds: dict[str, list[int]] | None, axis: str) -> int:
    if bounds is None:
        return 0
    return int(bounds[axis][1] - bounds[axis][0])


def safe_ratio(numerator: float, denominator: float) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 6)


def iou_for_cells(reference_cells: set[tuple[int, int, int]], candidate_cells: set[tuple[int, int, int]]) -> float:
    union = reference_cells | candidate_cells
    if not union:
        return 1.0
    return len(reference_cells & candidate_cells) / len(union)


def _transform_cells_xz(
    cells: set[tuple[int, int, int]],
    transform: Callable[[int, int], tuple[int, int]],
) -> set[tuple[int, int, int]]:
    return {(new_x, y, new_z) for x, y, z in cells for new_x, new_z in [transform(x, z)]}


XZ_ALIGNMENT_TRANSFORMS: dict[str, Callable[[int, int], tuple[int, int]]] = {
    "identity": lambda x, z: (x, z),
    "rotate_90": lambda x, z: (-z, x),
    "rotate_180": lambda x, z: (-x, -z),
    "rotate_270": lambda x, z: (z, -x),
    "mirror_x": lambda x, z: (-x, z),
    "mirror_z": lambda x, z: (x, -z),
    "mirror_diagonal": lambda x, z: (z, x),
    "mirror_antidiagonal": lambda x, z: (-z, -x),
}


def find_best_xz_alignment(
    reference_cells: set[tuple[int, int, int]],
    candidate_cells: set[tuple[int, int, int]],
) -> tuple[set[tuple[int, int, int]], dict]:
    best_cells, best_offset = align_cells_to_reference_origin_with_offset(reference_cells, candidate_cells)
    best_score = iou_for_cells(reference_cells, best_cells)
    best_report = {
        "mode": "best-xz",
        "transform": "identity",
        "offset": list(best_offset),
        "iou": round(best_score, 6),
    }
    for transform_name, transform in XZ_ALIGNMENT_TRANSFORMS.items():
        transformed = _transform_cells_xz(candidate_cells, transform)
        aligned, offset = align_cells_to_reference_origin_with_offset(reference_cells, transformed)
        score = iou_for_cells(reference_cells, aligned)
        if score > best_score:
            best_score = score
            best_cells = aligned
            best_report = {
                "mode": "best-xz",
                "transform": transform_name,
                "offset": list(offset),
                "iou": round(score, 6),
            }
    return best_cells, best_report


def summarize_layer_diffs(
    reference_cells: set[tuple[int, int, int]],
    candidate_cells: set[tuple[int, int, int]],
) -> list[dict]:
    layers = sorted({cell[1] for cell in reference_cells | candidate_cells})
    diffs: list[dict] = []
    for layer in layers:
        reference_layer = {cell for cell in reference_cells if cell[1] == layer}
        candidate_layer = {cell for cell in candidate_cells if cell[1] == layer}
        shared = reference_layer & candidate_layer
        missing = reference_layer - candidate_layer
        extra = candidate_layer - reference_layer
        union = reference_layer | candidate_layer
        diffs.append(
            {
                "layer": layer,
                "reference_voxels": len(reference_layer),
                "candidate_voxels": len(candidate_layer),
                "shared_voxels": len(shared),
                "missing_voxels": len(missing),
                "extra_voxels": len(extra),
                "iou": round(len(shared) / len(union), 6) if union else 1.0,
                "reference_bounds_xz": xz_bounds(reference_layer),
                "candidate_bounds_xz": xz_bounds(candidate_layer),
                "missing_bounds_xz": xz_bounds(missing),
                "extra_bounds_xz": xz_bounds(extra),
            }
        )
    return diffs


def summarize_layer_profiles(
    reference_cells: set[tuple[int, int, int]],
    candidate_cells: set[tuple[int, int, int]],
) -> list[dict]:
    layers = sorted({cell[1] for cell in reference_cells | candidate_cells})
    profiles: list[dict] = []
    for layer in layers:
        reference_layer = {cell for cell in reference_cells if cell[1] == layer}
        candidate_layer = {cell for cell in candidate_cells if cell[1] == layer}
        reference_bounds = xz_bounds(reference_layer)
        candidate_bounds = xz_bounds(candidate_layer)
        reference_area = len(reference_layer)
        candidate_area = len(candidate_layer)
        reference_width = bounds_size(reference_bounds, "x")
        reference_depth = bounds_size(reference_bounds, "z")
        candidate_width = bounds_size(candidate_bounds, "x")
        candidate_depth = bounds_size(candidate_bounds, "z")
        profiles.append(
            {
                "layer": layer,
                "reference_area": reference_area,
                "candidate_area": candidate_area,
                "area_delta": candidate_area - reference_area,
                "area_ratio": safe_ratio(candidate_area, reference_area),
                "reference_width": reference_width,
                "candidate_width": candidate_width,
                "width_delta": candidate_width - reference_width,
                "width_ratio": safe_ratio(candidate_width, reference_width),
                "reference_depth": reference_depth,
                "candidate_depth": candidate_depth,
                "depth_delta": candidate_depth - reference_depth,
                "depth_ratio": safe_ratio(candidate_depth, reference_depth),
                "reference_bounds_xz": reference_bounds,
                "candidate_bounds_xz": candidate_bounds,
            }
        )
    return profiles


def summarize_profile_deltas(
    reference_cells: set[tuple[int, int, int]],
    candidate_cells: set[tuple[int, int, int]],
    layer_profiles: list[dict],
) -> dict:
    reference_bounds = cell_bounds(reference_cells)
    candidate_bounds = cell_bounds(candidate_cells)
    reference_area = len(reference_cells)
    candidate_area = len(candidate_cells)
    width_ratio = safe_ratio(bounds_size(candidate_bounds, "x"), bounds_size(reference_bounds, "x"))
    depth_ratio = safe_ratio(bounds_size(candidate_bounds, "z"), bounds_size(reference_bounds, "z"))
    layer_ratio = safe_ratio(bounds_size(candidate_bounds, "layers"), bounds_size(reference_bounds, "layers"))
    area_ratio = safe_ratio(candidate_area, reference_area)
    area_deltas = [profile["area_delta"] for profile in layer_profiles]
    return {
        "reference_total_area": reference_area,
        "candidate_total_area": candidate_area,
        "total_area_delta": candidate_area - reference_area,
        "total_area_ratio": area_ratio,
        "global_width_ratio": width_ratio,
        "global_depth_ratio": depth_ratio,
        "global_layer_ratio": layer_ratio,
        "mean_layer_area_delta": round(sum(area_deltas) / len(area_deltas), 6) if area_deltas else 0.0,
        "most_underfilled_layers": sorted(layer_profiles, key=lambda item: item["area_delta"])[:10],
        "most_overfilled_layers": sorted(layer_profiles, key=lambda item: item["area_delta"], reverse=True)[:10],
    }


def build_profile_correction_hints(profile_summary: dict) -> list[dict]:
    hints: list[dict] = []
    width_ratio = profile_summary.get("global_width_ratio")
    depth_ratio = profile_summary.get("global_depth_ratio")
    layer_ratio = profile_summary.get("global_layer_ratio")
    area_ratio = profile_summary.get("total_area_ratio")
    if isinstance(width_ratio, (int, float)) and width_ratio < 0.9:
        hints.append(
            {
                "type": "compressed_width",
                "severity": "high" if width_ratio < 0.75 else "medium",
                "ratio": width_ratio,
                "suggestion": "Increase horizontal sampling resolution or inspect X-axis scaling/orientation.",
            }
        )
    if isinstance(depth_ratio, (int, float)) and depth_ratio < 0.9:
        hints.append(
            {
                "type": "compressed_depth",
                "severity": "high" if depth_ratio < 0.75 else "medium",
                "ratio": depth_ratio,
                "suggestion": "Increase depth sampling resolution or inspect Z-axis scaling/orientation.",
            }
        )
    if isinstance(layer_ratio, (int, float)) and (layer_ratio < 0.9 or layer_ratio > 1.1):
        hints.append(
            {
                "type": "height_mismatch",
                "severity": "medium",
                "ratio": layer_ratio,
                "suggestion": "Check target-studs scaling and source up-axis detection.",
            }
        )
    if isinstance(area_ratio, (int, float)) and area_ratio > 1.15:
        hints.append(
            {
                "type": "overfilled_layers",
                "severity": "high" if area_ratio > 1.35 else "medium",
                "ratio": area_ratio,
                "suggestion": "Use contour cleanup or a less aggressive ray-fill mode before optimizer work.",
            }
        )
    if isinstance(area_ratio, (int, float)) and area_ratio < 0.85:
        hints.append(
            {
                "type": "underfilled_layers",
                "severity": "medium",
                "ratio": area_ratio,
                "suggestion": "Use a broader ray-fill mode or reduce contour cleanup aggressiveness.",
            }
        )
    return hints


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
            summary["footprint_bounds_studs"] = cell_bounds(cells)
    return summary


def compare_ldr_footprints(
    reference_parts: list[LdrPart],
    candidate_parts: list[LdrPart],
    footprints: dict[str, StudioPartFootprint],
    *,
    align_origin: bool = True,
    alignment: str = "origin",
) -> dict:
    if alignment not in {"none", "origin", "best-xz"}:
        raise ValueError(f"Unsupported alignment mode: {alignment}")
    reference_cells = footprint_cells(reference_parts, footprints)
    candidate_cells = footprint_cells(candidate_parts, footprints)
    alignment_report = {"mode": "none", "transform": "identity", "offset": [0, 0, 0]}
    if align_origin and alignment == "origin":
        candidate_cells, offset = align_cells_to_reference_origin_with_offset(reference_cells, candidate_cells)
        alignment_report = {"mode": "origin", "transform": "identity", "offset": list(offset)}
    elif alignment == "best-xz":
        candidate_cells, alignment_report = find_best_xz_alignment(reference_cells, candidate_cells)
    shared = reference_cells & candidate_cells
    missing = reference_cells - candidate_cells
    extra = candidate_cells - reference_cells
    union = reference_cells | candidate_cells
    layer_diffs = summarize_layer_diffs(reference_cells, candidate_cells)
    layer_profiles = summarize_layer_profiles(reference_cells, candidate_cells)
    profile_summary = summarize_profile_deltas(reference_cells, candidate_cells, layer_profiles)
    return {
        "reference_voxel_count": len(reference_cells),
        "candidate_voxel_count": len(candidate_cells),
        "shared_voxel_count": len(shared),
        "missing_voxel_count": len(missing),
        "extra_voxel_count": len(extra),
        "iou": round(len(shared) / len(union), 6) if union else 1.0,
        "aligned_origin": alignment == "best-xz" or (alignment == "origin" and align_origin),
        "alignment": alignment_report,
        "reference_bounds_studs": cell_bounds(reference_cells),
        "candidate_bounds_studs": cell_bounds(candidate_cells),
        "layer_diffs": layer_diffs,
        "layer_profiles": layer_profiles,
        "profile_summary": profile_summary,
        "profile_correction_hints": build_profile_correction_hints(profile_summary),
        "worst_missing_layers": sorted(layer_diffs, key=lambda item: item["missing_voxels"], reverse=True)[:10],
        "worst_extra_layers": sorted(layer_diffs, key=lambda item: item["extra_voxels"], reverse=True)[:10],
        "worst_iou_layers": sorted(layer_diffs, key=lambda item: item["iou"])[:10],
        "reference_summary": summarize_ldr_parts(reference_parts, footprints),
        "candidate_summary": summarize_ldr_parts(candidate_parts, footprints),
    }


def write_json(data: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
