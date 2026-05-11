from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.studio.analysis import (
    extract_model_ldr,
    load_studio_brick_footprints,
    parse_ldr_parts,
    summarize_ldr_parts,
    write_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a BrickLink Studio .io or LDraw model.")
    parser.add_argument("--input", type=Path, required=True, help="Input .io or .ldr file.")
    parser.add_argument(
        "--studio-dir",
        type=Path,
        default=Path("Studio 2.0"),
        help="Optional Studio installation directory for part footprint metadata.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/reports/studio_io_analysis.json"),
        help="Output JSON report path.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    footprints = load_studio_brick_footprints(args.studio_dir) if args.studio_dir.exists() else None
    text = extract_model_ldr(args.input)
    parts = parse_ldr_parts(text)
    report = summarize_ldr_parts(parts, footprints)
    report["input"] = str(args.input)
    report["studio_dir"] = str(args.studio_dir) if footprints is not None else None
    write_json(report, args.output)
    print(f"Wrote Studio analysis report to {args.output}")


if __name__ == "__main__":
    main()
