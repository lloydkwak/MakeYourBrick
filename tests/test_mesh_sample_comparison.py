from __future__ import annotations

import json
from pathlib import Path

import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.quality.mesh_samples import SAMPLE_NAMES, compare_mesh_samples, create_sample_mesh


def test_create_sample_meshes_are_triangle_meshes() -> None:
    for sample in SAMPLE_NAMES:
        mesh = create_sample_mesh(sample)

        assert isinstance(mesh, trimesh.Trimesh)
        assert len(mesh.faces) > 0


def test_compare_mesh_samples_writes_summary_and_artifacts() -> None:
    output_dir = Path("outputs/quality/test_mesh_samples")
    try:
        summary = compare_mesh_samples(output_dir, samples=("sphere",), target_studs=5)

        summary_path = Path(summary["summary_path"])
        assert summary_path.exists()
        loaded = json.loads(summary_path.read_text(encoding="utf-8"))
        assert loaded["samples"][0]["sample"] == "sphere"
        assert Path(loaded["samples"][0]["ldr_path"]).exists()
        assert loaded["samples"][0]["stability"]["layer_count"] > 0
    finally:
        for path in sorted(output_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        output_dir.rmdir() if output_dir.exists() else None
