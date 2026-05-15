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
    parser = argparse.ArgumentParser(description="Convert an OBJ/STL mesh to a Studio-like LDraw sculpture.")
    parser.add_argument("--mesh", type=Path, required=True, help="Input OBJ/STL mesh path.")
    parser.add_argument("--base-size-studs", type=int, default=DEFAULT_BASE_SIZE_STUDS)
    parser.add_argument("--wall-thickness", type=int, default=DEFAULT_WALL_THICKNESS)
    parser.add_argument("--base-thickness", type=int, default=DEFAULT_BASE_THICKNESS)
    parser.add_argument("--up-axis", choices=("auto", "none", "x", "y", "z"), default="auto")
    parser.add_argument("--min-pitch", type=float, default=0.005)
    parser.add_argument("--voxels", type=Path, default=Path("outputs/voxels/model_voxels.npz"))
    parser.add_argument("--report", type=Path, default=Path("outputs/reports/model_report.json"))
    parser.add_argument("--output", type=Path, default=Path("outputs/ldr/model_output.ldr"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = convert_mesh_to_ldr(
        mesh_path=args.mesh,
        ldr_output_path=args.output,
        voxel_output_path=args.voxels,
        report_path=args.report,
        base_size_studs=args.base_size_studs,
        wall_thickness=args.wall_thickness,
        base_thickness=args.base_thickness,
        up_axis=args.up_axis,
        min_pitch=args.min_pitch,
    )
    print(f"Wrote LDraw model to {output_path}")


if __name__ == "__main__":
    main()
