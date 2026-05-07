from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--mask", type=Path)
    parser.add_argument("--record-json", type=Path)
    parser.add_argument("--exit-code", type=int, default=0)
    parser.add_argument("--colored-box", action="store_true")
    args = parser.parse_args()
    if args.exit_code:
        raise SystemExit(args.exit_code)
    if args.mask is not None and not args.mask.exists():
        raise FileNotFoundError(args.mask)
    if args.record_json is not None:
        args.record_json.parent.mkdir(parents=True, exist_ok=True)
        args.record_json.write_text(
            json.dumps({"mask": str(args.mask) if args.mask is not None else None}, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.colored_box:
        import numpy as np
        import trimesh

        mesh = trimesh.creation.box(extents=(1, 1, 1))
        mesh.visual.vertex_colors = np.tile(
            np.asarray([[242, 205, 55, 255]], dtype=np.uint8),
            (len(mesh.vertices), 1),
        )
        mesh.export(args.output)
        return
    args.output.write_bytes(b"mesh")


if __name__ == "__main__":
    main()
