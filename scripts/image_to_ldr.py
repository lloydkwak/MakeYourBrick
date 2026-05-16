from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.ai.sam3d_runner import Sam3DRunner
from makeyourbrick.pipeline import (
    DEFAULT_BASE_SIZE_STUDS,
    DEFAULT_BASE_THICKNESS,
    DEFAULT_WALL_THICKNESS,
    run_from_image,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert an image to a Studio-like LDraw sculpture through SAM 3D.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--sam-repo", type=Path, default=Path("third_party/sam-3d-objects"))
    parser.add_argument("--sam-command", required=True)
    parser.add_argument("--sam-timeout", type=int, default=3600)
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
        default="mesh",
        help="Use Studio-like layer colors or mesh-sampled LDraw color matching.",
    )
    parser.add_argument("--min-pitch", type=float, default=0.005)
    parser.add_argument("--raw-mesh", type=Path, default=Path("outputs/meshes/raw_model.glb"))
    parser.add_argument("--voxels", type=Path, default=Path("outputs/voxels/model_voxels.npz"))
    parser.add_argument("--report", type=Path, default=Path("outputs/reports/image_report.json"))
    parser.add_argument("--raw-mesh-report", type=Path)
    parser.add_argument("--output", type=Path, default=Path("outputs/ldr/image_output.ldr"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runner = Sam3DRunner(args.sam_repo, command_template=args.sam_command, timeout_seconds=args.sam_timeout)
    base_size_studs = args.base_size_studs if args.base_size_studs == "auto" else int(args.base_size_studs)
    output_path = run_from_image(
        image_path=args.image,
        runner=runner,
        mask_path=args.mask,
        raw_mesh_path=args.raw_mesh,
        voxel_output_path=args.voxels,
        ldr_output_path=args.output,
        report_path=args.report,
        raw_mesh_report_path=args.raw_mesh_report,
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
