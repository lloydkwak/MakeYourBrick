from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.quality.mesh_samples import SAMPLE_NAMES, compare_mesh_samples
from makeyourbrick.voxel.sculpture import SCULPTURE_MODES


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
    )
    print(f"Wrote mesh sample comparison to {summary['summary_path']}")


if __name__ == "__main__":
    main()
