from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.pipeline import convert_mesh_to_ldr


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a mesh file to a 1x1-brick LDraw model.")
    parser.add_argument("--mesh", type=Path, required=True, help="Input mesh path: .glb, .obj, .stl, etc.")
    parser.add_argument("--target-studs", type=int, default=24, help="Longest model extent in studs.")
    parser.add_argument("--min-pitch", type=float, default=0.005, help="Minimum voxel pitch.")
    parser.add_argument("--color", type=int, default=16, help="Default LDraw color id.")
    parser.add_argument(
        "--rgb",
        nargs=3,
        type=int,
        metavar=("R", "G", "B"),
        help="Constant voxel RGB color to quantize through the LDraw palette.",
    )
    parser.add_argument(
        "--palette",
        type=Path,
        default=Path("data/ldraw/ldraw_colors.json"),
        help="LDraw palette JSON path used with --rgb.",
    )
    parser.add_argument("--no-fill", action="store_true", help="Skip voxel fill.")
    parser.add_argument(
        "--cleaned-mesh",
        type=Path,
        default=Path("outputs/meshes/watertight_model.glb"),
        help="Cleaned mesh artifact path.",
    )
    parser.add_argument(
        "--voxels",
        type=Path,
        default=Path("outputs/voxels/model_voxels.npz"),
        help="Voxel artifact path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/ldr/mesh_output.ldr"),
        help="Output LDraw path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_path = convert_mesh_to_ldr(
        mesh_path=args.mesh,
        ldr_output_path=args.output,
        cleaned_mesh_path=args.cleaned_mesh,
        voxel_output_path=args.voxels,
        target_longest_studs=args.target_studs,
        min_pitch=args.min_pitch,
        fill=not args.no_fill,
        default_color_id=args.color,
        default_rgb=tuple(args.rgb) if args.rgb else None,
        palette_path=args.palette,
    )
    print(f"Wrote LDraw model to {output_path}")


if __name__ == "__main__":
    main()
