from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_image_to_ldr_cli_runs_fake_sam_command_to_ldr() -> None:
    image_path = Path("outputs/test_cli_image.png")
    raw_mesh = Path("outputs/meshes/test_cli_image_raw.ply")
    cleaned_mesh = Path("outputs/meshes/test_cli_image_cleaned.glb")
    voxel_path = Path("outputs/voxels/test_cli_image_voxels.npz")
    ldr_path = Path("outputs/ldr/test_cli_image.ldr")
    report_path = Path("outputs/reports/test_cli_image_report.json")
    try:
        image_path.write_bytes(b"fake-image")
        command = f"{sys.executable} tests/fake_sam3d_command.py --output {{output}} --colored-box"

        subprocess.run(
            [
                sys.executable,
                "scripts/image_to_ldr.py",
                "--image",
                str(image_path),
                "--sam-repo",
                ".",
                "--sam-command",
                command,
                "--target-studs",
                "8",
                "--sample-colors",
                "--optimize",
                "--raw-mesh",
                str(raw_mesh),
                "--cleaned-mesh",
                str(cleaned_mesh),
                "--voxels",
                str(voxel_path),
                "--report",
                str(report_path),
                "--output",
                str(ldr_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        brick_lines = [line for line in ldr_path.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert raw_mesh.exists()
        assert cleaned_mesh.exists()
        assert voxel_path.exists()
        assert brick_lines
        assert all(line.split()[1] == "14" for line in brick_lines)
        assert report["optimized"] is True
        assert report["output_brick_count"] == len(brick_lines)
    finally:
        image_path.unlink(missing_ok=True)
        raw_mesh.unlink(missing_ok=True)
        cleaned_mesh.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)

