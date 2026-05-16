from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.pipeline import (
    DEFAULT_BASE_SIZE_STUDS,
    DEFAULT_BASE_THICKNESS,
    DEFAULT_WALL_THICKNESS,
    convert_mesh_to_ldr,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert an OBJ/GLB/STL mesh to a Studio-like LDraw sculpture.")
    parser.add_argument("--mesh", type=Path, required=True, help="Input OBJ/GLB/STL mesh path.")
    parser.add_argument(
        "--base-size-studs",
        default=str(DEFAULT_BASE_SIZE_STUDS),
        help="Maximum horizontal footprint in studs, or 'auto' to choose from 16/24/32/48/64.",
    )
    parser.add_argument("--wall-thickness", type=int, default=DEFAULT_WALL_THICKNESS)
    parser.add_argument("--base-thickness", type=int, default=DEFAULT_BASE_THICKNESS)
    parser.add_argument("--up-axis", choices=("auto", "none", "x", "y", "z"), default="auto")
    parser.add_argument(
        "--color-strategy",
        choices=("layer", "mesh"),
        default="layer",
        help="Use Studio-like layer colors or mesh-sampled LDraw color matching.",
    )
    parser.add_argument("--min-pitch", type=float, default=0.005)
    parser.add_argument("--voxels", type=Path, default=Path("outputs/voxels/model_voxels.npz"))
    parser.add_argument("--report", type=Path, default=Path("outputs/reports/model_report.json"))
    parser.add_argument(
        "--debug-target-output",
        type=Path,
        help="Optional LDraw output where every target voxel is emitted as a 1x1 brick.",
    )
    parser.add_argument("--output", type=Path, default=Path("outputs/ldr/model_output.ldr"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    base_size_studs = args.base_size_studs if args.base_size_studs == "auto" else int(args.base_size_studs)
    output_path = convert_mesh_to_ldr(
        mesh_path=args.mesh,
        ldr_output_path=args.output,
        voxel_output_path=args.voxels,
        report_path=args.report,
        debug_target_ldr_path=args.debug_target_output,
        base_size_studs=base_size_studs,
        wall_thickness=args.wall_thickness,
        base_thickness=args.base_thickness,
        up_axis=args.up_axis,
        min_pitch=args.min_pitch,
        color_strategy=args.color_strategy,
    )
    print(f"Wrote LDraw model to {output_path}")


if __name__ == "__main__":
    main()
