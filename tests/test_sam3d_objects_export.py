from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")


SCRIPT_PATH = Path("scripts/adapters/run_sam3d_objects_export.py")
SPEC = importlib.util.spec_from_file_location("run_sam3d_objects_export", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
sam3d_export = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sam3d_export)


class FakeGlb:
    def __init__(self) -> None:
        self.exported_path: Path | None = None

    def export(self, path: Path) -> None:
        self.exported_path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(path)


class FakeSplat:
    def save_ply(self, path: str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "\n".join(
                [
                    "ply",
                    "format ascii 1.0",
                    "element vertex 1",
                    "property float x",
                    "property float y",
                    "property float z",
                    "property float opacity",
                    "property float scale_0",
                    "end_header",
                    "0 0 0 1 0.1",
                ]
            )
            + "\n",
            encoding="ascii",
        )


class FakeTensor:
    def __init__(self, value) -> None:
        self.value = np.asarray(value)

    def detach(self):
        return self

    def cpu(self):
        return self

    def numpy(self):
        return self.value


class FakeMesh:
    def __init__(self) -> None:
        self.vertices = FakeTensor(
            [
                [0, 0, 0],
                [1, 0, 0],
                [0, 1, 0],
                [0, 0, 1],
            ]
        )
        self.faces = FakeTensor(
            [
                [0, 1, 2],
                [0, 1, 3],
                [0, 2, 3],
                [1, 2, 3],
            ]
        )


def test_export_sam3d_output_prefers_glb_export() -> None:
    output_path = Path("outputs/meshes/test_sam3d_real_export_glb.glb")
    splat_path = Path("outputs/meshes/test_sam3d_real_export_splat.ply")
    glb = FakeGlb()
    try:
        metadata = sam3d_export.export_sam3d_output(
            {"glb": glb, "mesh": [FakeMesh()], "gs": FakeSplat()},
            output_path,
            splat_output_path=splat_path,
        )

        assert output_path.exists()
        assert splat_path.exists()
        assert glb.exported_path == output_path
        assert metadata["export_method"] == "output_glb"
        assert metadata["splat_output_path"] == str(splat_path)
    finally:
        output_path.unlink(missing_ok=True)
        splat_path.unlink(missing_ok=True)


def test_export_sam3d_output_falls_back_to_mesh_vertices_faces() -> None:
    output_path = Path("outputs/meshes/test_sam3d_real_export_mesh.glb")
    try:
        metadata = sam3d_export.export_sam3d_output({"mesh": [FakeMesh()]}, output_path)
        loaded = trimesh.load(output_path)

        assert output_path.exists()
        assert metadata["export_method"] == "mesh_to_trimesh_glb"
        assert len(loaded.geometry) > 0 if isinstance(loaded, trimesh.Scene) else len(loaded.faces) > 0
    finally:
        output_path.unlink(missing_ok=True)


def test_export_sam3d_output_rejects_splat_only_output() -> None:
    output_path = Path("outputs/meshes/test_sam3d_real_export_missing.glb")
    splat_path = Path("outputs/meshes/test_sam3d_real_export_debug_splat.ply")
    try:
        with pytest.raises(ValueError, match="did not contain exportable GLB or triangle mesh"):
            sam3d_export.export_sam3d_output({"gs": FakeSplat()}, output_path, splat_output_path=splat_path)

        assert not output_path.exists()
        assert splat_path.exists()
    finally:
        output_path.unlink(missing_ok=True)
        splat_path.unlink(missing_ok=True)
