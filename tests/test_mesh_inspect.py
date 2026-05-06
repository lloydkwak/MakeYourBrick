from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.mesh.inspect import inspect_mesh, inspect_mesh_to_file


def test_inspect_mesh_reports_triangle_mesh_readiness() -> None:
    mesh_path = Path("outputs/meshes/test_inspect_box.glb")
    report_path = Path("outputs/reports/test_inspect_box.json")
    try:
        mesh_path.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 2, 3)).export(mesh_path)

        report = inspect_mesh_to_file(mesh_path, report_path)

        assert report["load_status"] == "loaded"
        assert report["asset_type"] in {"triangle_mesh", "scene"}
        assert report["vertex_count"] > 0
        assert report["face_count"] > 0
        assert report["voxelization_ready"] is True
        assert json.loads(report_path.read_text(encoding="utf-8"))["face_count"] == report["face_count"]
    finally:
        mesh_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)


def test_inspect_mesh_reports_missing_file() -> None:
    report = inspect_mesh(Path("outputs/meshes/missing_inspect_mesh.glb"))

    assert report["exists"] is False
    assert report["load_status"] == "failed"
    assert report["voxelization_ready"] is False
    assert report["errors"]


def test_inspect_mesh_cli_writes_report() -> None:
    mesh_path = Path("outputs/meshes/test_inspect_cli_box.glb")
    report_path = Path("outputs/reports/test_inspect_cli_box.json")
    try:
        mesh_path.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(mesh_path)

        result = subprocess.run(
            [
                sys.executable,
                "scripts/inspect_mesh.py",
                "--mesh",
                str(mesh_path),
                "--report",
                str(report_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert "Mesh inspection ready" in result.stdout
        assert report["voxelization_ready"] is True
    finally:
        mesh_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
