from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.pipeline import convert_mesh_to_ldr
from makeyourbrick.mesh.repair import REPAIR_MODES
from makeyourbrick.mesh.orient import UP_AXIS_OPTIONS
from makeyourbrick.voxel.voxelize import RAY_FILL_MODES, VOXELIZERS
from makeyourbrick.voxel.sculpture import INFILL_PATTERNS, SCULPTURE_MODES, VOXEL_SMOOTHING_PRESETS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a mesh file to a 1x1-brick LDraw model.")
    parser.add_argument("--mesh", type=Path, required=True, help="Input mesh path: .glb, .obj, .stl, etc.")
    parser.add_argument("--target-studs", type=int, default=24, help="Longest model extent in studs.")
    parser.add_argument("--target-width-studs", type=int, help="Optional Studio-style target X footprint in studs.")
    parser.add_argument("--target-depth-studs", type=int, help="Optional Studio-style target Z footprint in studs.")
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
        "--voxelizer",
        choices=VOXELIZERS,
        default="surface",
        help="Voxelization method. Use ray for layer-by-layer sculpture-style filling.",
    )
    parser.add_argument(
        "--ray-fill",
        choices=RAY_FILL_MODES,
        default="wide",
        help="Odd ray-hit fill strategy used by --voxelizer ray.",
    )
    parser.add_argument("--optimize", action="store_true", help="Merge voxels into larger bricks.")
    parser.add_argument(
        "--optimizer",
        choices=("greedy", "layered"),
        default="greedy",
        help="Brick optimizer to use when --optimize is enabled.",
    )
    parser.add_argument(
        "--sculpture-mode",
        choices=SCULPTURE_MODES,
        default="solid",
        help="Voxel occupancy mode before brickification.",
    )
    parser.add_argument("--wall-thickness", type=int, default=1, help="Shell wall thickness in studs.")
    parser.add_argument("--base-thickness", type=int, default=0, help="Solid base thickness in layers.")
    parser.add_argument(
        "--infill-density",
        type=float,
        default=0.35,
        help="Interior lattice density used by --sculpture-mode density.",
    )
    parser.add_argument(
        "--infill-pattern",
        choices=INFILL_PATTERNS,
        default="lattice",
        help="Interior support pattern used by --sculpture-mode density.",
    )
    parser.add_argument(
        "--voxel-smoothing",
        choices=VOXEL_SMOOTHING_PRESETS,
        default="none",
        help="Optional sculpture voxel cleanup preset.",
    )
    parser.add_argument("--steps-by-layer", action="store_true", help="Insert LDraw 0 STEP markers per layer.")
    parser.add_argument(
        "--sample-colors",
        action="store_true",
        help="Sample nearest mesh vertex or face colors into voxels.",
    )
    parser.add_argument("--report", type=Path, help="Optional optimizer report JSON path.")
    parser.add_argument(
        "--repair-mode",
        choices=REPAIR_MODES,
        default="basic",
        help="Mesh repair mode before voxelization.",
    )
    parser.add_argument(
        "--up-axis",
        choices=UP_AXIS_OPTIONS,
        default="auto",
        help="Source mesh up axis. Auto maps a clearly dominant longest axis to LDraw vertical.",
    )
    parser.add_argument("--repair-report", type=Path, help="Optional mesh repair report JSON path.")
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
        target_width_studs=args.target_width_studs,
        target_depth_studs=args.target_depth_studs,
        fill=not args.no_fill,
        voxelizer=args.voxelizer,
        ray_fill=args.ray_fill,
        default_color_id=args.color,
        default_rgb=tuple(args.rgb) if args.rgb else None,
        palette_path=args.palette,
        optimize=args.optimize,
        optimizer=args.optimizer,
        sample_colors=args.sample_colors,
        report_path=args.report,
        repair_mode=args.repair_mode,
        repair_report_path=args.repair_report,
        up_axis=args.up_axis,
        sculpture_mode=args.sculpture_mode,
        wall_thickness=args.wall_thickness,
        base_thickness=args.base_thickness,
        voxel_smoothing=args.voxel_smoothing,
        infill_density=args.infill_density,
        infill_pattern=args.infill_pattern,
        steps_by_layer=args.steps_by_layer,
    )
    print(f"Wrote LDraw model to {output_path}")


if __name__ == "__main__":
    main()
