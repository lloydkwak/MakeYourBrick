from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.brickify.optimizer import BRICK_PALETTES
from makeyourbrick.quality.mesh_samples import SAMPLE_NAMES, compare_mesh_samples
from makeyourbrick.voxel.sculpture import INFILL_PATTERNS, SCULPTURE_MODES, VOXEL_SMOOTHING_PRESETS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare brickification quality on standard mesh samples.")
    parser.add_argument(
        "--samples",
        nargs="+",
        choices=SAMPLE_NAMES,
        default=list(SAMPLE_NAMES),
        help="Sample mesh names to generate and convert.",
    )
    parser.add_argument("--target-studs", type=int, default=8, help="Longest model extent in studs.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/quality/mesh_samples"),
        help="Directory for generated meshes, LDRs, and reports.",
    )
    parser.add_argument(
        "--sculpture-mode",
        choices=SCULPTURE_MODES,
        default="shell",
        help="Voxel occupancy mode before brickification.",
    )
    parser.add_argument("--wall-thickness", type=int, default=1, help="Shell wall thickness in studs.")
    parser.add_argument("--base-thickness", type=int, default=1, help="Solid base thickness in layers.")
    parser.add_argument(
        "--brick-palette",
        choices=BRICK_PALETTES,
        default="full",
        help="Brick candidate palette used by the optimizer.",
    )
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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = compare_mesh_samples(
        args.output_dir,
        samples=tuple(args.samples),
        target_studs=args.target_studs,
        sculpture_mode=args.sculpture_mode,
        wall_thickness=args.wall_thickness,
        base_thickness=args.base_thickness,
        infill_density=args.infill_density,
        infill_pattern=args.infill_pattern,
        voxel_smoothing=args.voxel_smoothing,
        brick_palette=args.brick_palette,
    )
    print(f"Wrote mesh sample comparison to {summary['summary_path']}")


if __name__ == "__main__":
    main()
