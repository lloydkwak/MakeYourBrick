from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.io.ldr_writer import write_ldr
from makeyourbrick.types import Brick


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an LDraw placement check fixture.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/ldr/ldraw_placement_check.ldr"),
        help="Output .ldr path.",
    )
    parser.add_argument("--steps-by-layer", action="store_true", help="Insert layer STEP markers.")
    return parser.parse_args()


def placement_fixture_bricks() -> list[Brick]:
    return [
        Brick("3005.dat", color_id=14, x=0, y=0, z=0, width=1, depth=1),
        Brick("3004.dat", color_id=4, x=2, y=0, z=0, width=1, depth=2),
        Brick("3003.dat", color_id=2, x=4, y=0, z=0, width=2, depth=2),
        Brick("3010.dat", color_id=1, x=7, y=0, z=0, width=1, depth=4),
        Brick("3001.dat", color_id=15, x=9, y=0, z=0, width=2, depth=4),
        Brick("3001.dat", color_id=16, x=0, y=1, z=4, width=4, depth=2, rotation_degrees=90),
    ]


def main() -> None:
    args = parse_args()
    bricks = placement_fixture_bricks()
    write_ldr(bricks, args.output, title="LDraw placement check", step_by_layer=args.steps_by_layer)
    print(f"Wrote placement fixture with {len(bricks)} bricks to {args.output}")


if __name__ == "__main__":
    main()
