from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_make_synthetic_ldr_cli_writes_expected_brick_count() -> None:
    output_path = Path("outputs/ldr/test_cli_box.ldr")
    try:
        result = subprocess.run(
            [
                sys.executable,
                "scripts/make_synthetic_ldr.py",
                "--shape",
                "box",
                "--size",
                "4",
                "3",
                "2",
                "--color",
                "14",
                "--output",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        lines = output_path.read_text(encoding="utf-8").splitlines()
        brick_lines = [line for line in lines if line.startswith("1 ")]
        assert "Wrote 24 bricks" in result.stdout
        assert len(brick_lines) == 24
        assert all(line.split()[1] == "14" for line in brick_lines)
    finally:
        output_path.unlink(missing_ok=True)


def test_make_synthetic_ldr_cli_can_write_optimized_bricks() -> None:
    output_path = Path("outputs/ldr/test_cli_optimized_box.ldr")
    try:
        subprocess.run(
            [
                sys.executable,
                "scripts/make_synthetic_ldr.py",
                "--shape",
                "box",
                "--size",
                "4",
                "1",
                "2",
                "--color",
                "16",
                "--optimize",
                "--output",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        brick_lines = [line for line in output_path.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
        assert len(brick_lines) == 1
        assert brick_lines[0].endswith("3001.dat")
        assert "0 0 1 0 1 0 -1 0 0" in brick_lines[0]
    finally:
        output_path.unlink(missing_ok=True)
