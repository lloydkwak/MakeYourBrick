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

