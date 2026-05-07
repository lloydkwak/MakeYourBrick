from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")


def make_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-image")


def make_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def test_sam3d_adapter_exports_candidate_triangle_mesh() -> None:
    repo = Path("outputs/test_sam_adapter_repo")
    image = Path("outputs/test_sam_adapter_image.png")
    candidate = Path("outputs/test_sam_adapter/raw_candidate.glb")
    output = Path("outputs/meshes/test_sam_adapter_output.glb")
    report_path = Path("outputs/reports/test_sam_adapter_report.json")
    try:
        make_repo(repo)
        make_image(image)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(candidate)

        result = subprocess.run(
            [
                sys.executable,
                "scripts/adapters/sam3d_to_mesh.py",
                "--repo",
                str(repo),
                "--image",
                str(image),
                "--candidate",
                str(candidate),
                "--output",
                str(output),
                "--report",
                str(report_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert "Adapted SAM output" in result.stdout
        assert output.exists()
        assert report["status"] == "completed"
        assert report["output_inspection"]["voxelization_ready"] is True
    finally:
        image.unlink(missing_ok=True)
        candidate.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)


def test_sam3d_adapter_runs_command_template_that_writes_output() -> None:
    image = Path("outputs/test_sam_adapter_command_image.png")
    output = Path("outputs/meshes/test_sam_adapter_command_output.glb")
    report_path = Path("outputs/reports/test_sam_adapter_command_report.json")
    try:
        make_image(image)
        command = f"{sys.executable} tests/fake_sam3d_command.py --output {{output}} --colored-box"

        subprocess.run(
            [
                sys.executable,
                "scripts/adapters/sam3d_to_mesh.py",
                "--repo",
                ".",
                "--image",
                str(image),
                "--sam-command",
                command,
                "--output",
                str(output),
                "--report",
                str(report_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert output.exists()
        assert report["candidate_path"] == str(output)
        assert report["output_inspection"]["face_count"] > 0
    finally:
        image.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)


def test_sam3d_adapter_rejects_point_cloud_candidate() -> None:
    repo = Path("outputs/test_sam_adapter_repo")
    image = Path("outputs/test_sam_adapter_point_image.png")
    candidate = Path("outputs/test_sam_adapter/point_cloud.ply")
    output = Path("outputs/meshes/test_sam_adapter_point_output.glb")
    try:
        make_repo(repo)
        make_image(image)
        candidate.parent.mkdir(parents=True, exist_ok=True)
        cloud = trimesh.points.PointCloud(np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float))
        cloud.export(candidate)

        result = subprocess.run(
            [
                sys.executable,
                "scripts/adapters/sam3d_to_mesh.py",
                "--repo",
                str(repo),
                "--image",
                str(image),
                "--candidate",
                str(candidate),
                "--output",
                str(output),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "triangle mesh" in result.stderr or "voxelization-ready" in result.stderr
        assert not output.exists()
    finally:
        image.unlink(missing_ok=True)
        candidate.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
