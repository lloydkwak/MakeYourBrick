from __future__ import annotations

import argparse
from pathlib import Path

from makeyourbrick.pipeline import run_from_image, run_from_mesh


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert an image or mesh into an LDraw LEGO model.")
    parser.add_argument("--image", type=Path, help="Input image path for SAM 3D generation.")
    parser.add_argument("--mesh", type=Path, help="Existing mesh path for the non-AI path.")
    parser.add_argument("--skip-ai", action="store_true", help="Require --mesh and skip SAM 3D generation.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.skip_ai or args.mesh:
        if args.mesh is None:
            raise SystemExit("--mesh is required when --skip-ai is set.")
        artifact = run_from_mesh(args.mesh)
        print(f"Loaded mesh artifact: {artifact.path}")
        return
    if args.image is None:
        raise SystemExit("Provide --image or --mesh --skip-ai.")
    output = run_from_image(args.image)
    print(f"Wrote LDR: {output}")


if __name__ == "__main__":
    main()

