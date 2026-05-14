from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.ai.sam3d_runner import Sam3DRunner
from makeyourbrick.brickify.optimizer import BRICK_PALETTES
from makeyourbrick.mesh.orient import UP_AXIS_OPTIONS
from makeyourbrick.mesh.repair import REPAIR_MODES
from makeyourbrick.pipeline import COLOR_STRATEGIES, HEIGHT_UNITS, SCULPTURE_ENGINES, run_from_image
from makeyourbrick.voxel.sculpture import INFILL_PATTERNS, SCULPTURE_MODES, VOXEL_SMOOTHING_PRESETS
from makeyourbrick.voxel.voxelize import RAY_FILL_MODES, VOXELIZERS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert an image to an LDraw model through SAM 3D.")
    parser.add_argument("--image", type=Path, required=True, help="Input image path.")
    parser.add_argument("--mask", type=Path, help="Optional object mask path for SAM 3D object selection.")
    parser.add_argument(
        "--sam-repo",
        type=Path,
        default=Path("third_party/sam-3d-objects"),
        help="External SAM 3D Objects repo path.",
    )
    parser.add_argument(
        "--sam-command",
        required=True,
        help="SAM command template. Supports {image}, {mask}, {output}, {output_dir}, and {repo}.",
    )
    parser.add_argument("--sam-timeout", type=int, default=3600, help="SAM command timeout in seconds.")
    parser.add_argument("--target-studs", type=int, default=48, help="Longest model extent in studs.")
    parser.add_argument("--base-size-studs", type=int, help="Uniform Studio-style base footprint size in studs.")
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
        help="LDraw palette JSON path.",
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
    parser.add_argument("--sample-colors", action="store_true", help="Sample nearest mesh colors into voxels.")
    parser.add_argument("--optimize", action="store_true", help="Merge voxels into larger bricks.")
    parser.add_argument(
        "--optimizer",
        choices=("greedy", "layered"),
        default="greedy",
        help="Brick optimizer to use when --optimize is enabled.",
    )
    parser.add_argument(
        "--brick-palette",
        choices=BRICK_PALETTES,
        default="full",
        help="Brick candidate palette used when --optimize is enabled.",
    )
    parser.add_argument(
        "--height-unit",
        choices=HEIGHT_UNITS,
        default="brick",
        help="Vertical output unit. Use plate with --brick-palette plates for one-third brick-height layers.",
    )
    parser.add_argument(
        "--sculpture-mode",
        choices=SCULPTURE_MODES,
        default="solid",
        help="Voxel occupancy mode before brickification.",
    )
    parser.add_argument(
        "--sculpture-engine",
        choices=SCULPTURE_ENGINES,
        default="legacy",
        help="Sculpture conversion engine. Use layered for Studio-like target and placement separation.",
    )
    parser.add_argument("--wall-thickness", type=int, default=1, help="Shell wall thickness in studs.")
    parser.add_argument("--base-thickness", type=int, default=0, help="Solid base thickness in layers.")
    parser.add_argument("--support-spacing", type=int, default=3, help="Sparse support column spacing.")
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
    parser.add_argument(
        "--color-strategy",
        choices=COLOR_STRATEGIES,
        default="strict",
        help="Use strict color boundaries or majority per-brick color assignment.",
    )
    parser.add_argument("--steps-by-layer", action="store_true", help="Insert LDraw 0 STEP markers per layer.")
    parser.add_argument("--raw-mesh", type=Path, default=Path("outputs/meshes/raw_model.obj"))
    parser.add_argument("--cleaned-mesh", type=Path, default=Path("outputs/meshes/cleaned_model.obj"))
    parser.add_argument("--voxels", type=Path, default=Path("outputs/voxels/model_voxels.npz"))
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
    parser.add_argument("--output", type=Path, default=Path("outputs/ldr/image_output.ldr"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runner = Sam3DRunner(
        repo_path=args.sam_repo,
        command_template=args.sam_command,
        timeout_seconds=args.sam_timeout,
    )
    output_path = run_from_image(
        image_path=args.image,
        runner=runner,
        mask_path=args.mask,
        raw_mesh_path=args.raw_mesh,
        cleaned_mesh_path=args.cleaned_mesh,
        voxel_output_path=args.voxels,
        ldr_output_path=args.output,
        target_longest_studs=args.target_studs,
        min_pitch=args.min_pitch,
        base_size_studs=args.base_size_studs,
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
        brick_palette=args.brick_palette,
        height_unit=args.height_unit,
        sample_colors=args.sample_colors,
        report_path=args.report,
        repair_mode=args.repair_mode,
        repair_report_path=args.repair_report,
        up_axis=args.up_axis,
        sculpture_mode=args.sculpture_mode,
        sculpture_engine=args.sculpture_engine,
        wall_thickness=args.wall_thickness,
        base_thickness=args.base_thickness,
        support_spacing=args.support_spacing,
        voxel_smoothing=args.voxel_smoothing,
        infill_density=args.infill_density,
        infill_pattern=args.infill_pattern,
        color_strategy=args.color_strategy,
        steps_by_layer=args.steps_by_layer,
    )
    print(f"Wrote LDraw model to {output_path}")


if __name__ == "__main__":
    main()
