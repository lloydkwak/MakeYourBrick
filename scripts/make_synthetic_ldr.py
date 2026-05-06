from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.brickify.optimizer import brickify_1x1
from makeyourbrick.io.ldr_writer import write_ldr
from makeyourbrick.voxel.synthetic import make_solid_box, make_stairs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a synthetic 1x1-brick LDraw model.")
    parser.add_argument("--shape", choices=("box", "stairs"), default="box")
    parser.add_argument(
        "--size",
        nargs=3,
        type=int,
        metavar=("WIDTH", "HEIGHT", "DEPTH"),
        default=(4, 3, 2),
        help="Box size or stairs width/steps/depth.",
    )
    parser.add_argument("--color", type=int, default=16, help="LDraw color id.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/ldr/synthetic_box.ldr"),
        help="Output .ldr path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    width, height, depth = args.size
    if args.shape == "box":
        occupancy, color_ids = make_solid_box((width, height, depth), color_id=args.color)
    else:
        occupancy, color_ids = make_stairs(width=width, steps=height, depth=depth, color_id=args.color)

    bricks = brickify_1x1(occupancy, color_ids)
    write_ldr(bricks, args.output, title=f"Synthetic {args.shape}")
    print(f"Wrote {len(bricks)} bricks to {args.output}")


if __name__ == "__main__":
    main()

