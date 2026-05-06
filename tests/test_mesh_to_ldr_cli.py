from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

trimesh = pytest.importorskip("trimesh")


def test_mesh_to_ldr_cli_converts_generated_stl_to_ldr() -> None:
    input_mesh = Path("outputs/meshes/test_cli_box.stl")
    cleaned_mesh = Path("outputs/meshes/test_cli_cleaned.glb")
    voxel_path = Path("outputs/voxels/test_cli_voxels.npz")
    ldr_path = Path("outputs/ldr/test_cli_mesh.ldr")
    try:
        input_mesh.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(input_mesh)

        result = subprocess.run(
            [
                sys.executable,
                "scripts/mesh_to_ldr.py",
                "--mesh",
                str(input_mesh),
                "--target-studs",
                "8",
                "--color",
                "14",
                "--cleaned-mesh",
                str(cleaned_mesh),
                "--voxels",
                str(voxel_path),
                "--output",
                str(ldr_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        lines = ldr_path.read_text(encoding="utf-8").splitlines()
        brick_lines = [line for line in lines if line.startswith("1 ")]
        assert "Wrote LDraw model" in result.stdout
        assert cleaned_mesh.exists()
        assert voxel_path.exists()
        assert brick_lines
        assert all(line.split()[1] == "14" for line in brick_lines)
    finally:
        input_mesh.unlink(missing_ok=True)
        cleaned_mesh.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)

