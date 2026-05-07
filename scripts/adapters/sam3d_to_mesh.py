from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from makeyourbrick.ai.sam3d_adapter import adapt_sam_output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Adapt SAM 3D output into a MakeYourBrick triangle mesh.")
    parser.add_argument("--repo", type=Path, required=True, help="SAM 3D Objects repository path.")
    parser.add_argument("--image", type=Path, required=True, help="Input image path.")
    parser.add_argument("--mask", type=Path, help="Optional object mask path.")
    parser.add_argument("--output", type=Path, required=True, help="Output triangle mesh path, usually .glb.")
    parser.add_argument(
        "--sam-command",
        help=(
            "Optional upstream SAM command template. Supports {repo}, {image}, {mask}, {output}, "
            "{output_dir}, and {work_dir}."
        ),
    )
    parser.add_argument(
        "--candidate",
        type=Path,
        help="Optional existing SAM artifact to adapt instead of searching command outputs.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Directory where upstream SAM outputs are written and searched.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("outputs/reports/sam3d_adapter.json"),
        help="Adapter report JSON path.",
    )
    parser.add_argument("--timeout", type=int, default=3600, help="SAM command timeout in seconds.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = adapt_sam_output(
        repo_path=args.repo,
        image_path=args.image,
        mask_path=args.mask,
        output_path=args.output,
        command_template=args.sam_command,
        candidate_path=args.candidate,
        work_dir=args.work_dir,
        report_path=args.report,
        timeout_seconds=args.timeout,
    )
    output = report["output_inspection"]
    print(
        "Adapted SAM output: "
        f"type={output['asset_type']} vertices={output['vertex_count']} "
        f"faces={output['face_count']} output={args.output}"
    )


if __name__ == "__main__":
    main()
