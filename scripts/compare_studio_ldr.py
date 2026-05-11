from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.studio.analysis import (
    compare_ldr_footprints,
    extract_model_ldr,
    load_studio_brick_footprints,
    parse_ldr_parts,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare MakeYourBrick LDR output against Studio .io/.ldr output.")
    parser.add_argument("--reference", type=Path, required=True, help="Studio .io or .ldr reference.")
    parser.add_argument("--candidate", type=Path, required=True, help="Candidate .ldr output.")
    parser.add_argument(
        "--studio-dir",
        type=Path,
        default=Path("Studio 2.0"),
        help="Studio installation directory for part footprint metadata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/studio_ldr_comparison.json"),
        help="Output JSON comparison path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    footprints = load_studio_brick_footprints(args.studio_dir)
    reference_parts = parse_ldr_parts(extract_model_ldr(args.reference))
    candidate_parts = parse_ldr_parts(extract_model_ldr(args.candidate))
    report = compare_ldr_footprints(reference_parts, candidate_parts, footprints)
    report["reference"] = str(args.reference)
    report["candidate"] = str(args.candidate)
    report["studio_dir"] = str(args.studio_dir)
    write_json(report, args.output)
    print(f"Wrote Studio comparison report to {args.output}")
    print(f"IoU={report['iou']} missing={report['missing_voxel_count']} extra={report['extra_voxel_count']}")


if __name__ == "__main__":
    main()
