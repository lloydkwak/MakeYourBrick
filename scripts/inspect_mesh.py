from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.mesh.inspect import inspect_mesh_to_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect a mesh artifact for MakeYourBrick compatibility.")
    parser.add_argument("--mesh", type=Path, required=True, help="Input mesh path.")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("outputs/reports/mesh_inspect.json"),
        help="Output JSON inspection report.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = inspect_mesh_to_file(args.mesh, args.report)
    status = "ready" if report["voxelization_ready"] else "not-ready"
    print(
        "Mesh inspection "
        f"{status}: type={report['asset_type']} "
        f"vertices={report['vertex_count']} faces={report['face_count']} "
        f"report={args.report}"
    )


if __name__ == "__main__":
    main()
