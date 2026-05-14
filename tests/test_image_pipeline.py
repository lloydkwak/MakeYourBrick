from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.pipeline import run_from_image
from makeyourbrick.types import MeshArtifact


class FakeImageToMeshRunner:
    def __init__(self) -> None:
        self.mask_path: Path | None = None

    def generate(self, image_path: Path, output_path: Path, mask_path: Path | None = None) -> MeshArtifact:
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        self.mask_path = mask_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mesh = trimesh.creation.box(extents=(1, 1, 1))
        mesh.visual.vertex_colors = np.tile(
            np.asarray([[242, 205, 55, 255]], dtype=np.uint8),
            (len(mesh.vertices), 1),
        )
        mesh.export(output_path)
        return MeshArtifact(path=output_path, source="fake-image-runner")


def test_run_from_image_generates_ldr_and_report_with_fake_runner() -> None:
    image_path = Path("outputs/test_input_image.png")
    raw_mesh_path = Path("outputs/meshes/test_image_raw.ply")
    cleaned_mesh_path = Path("outputs/meshes/test_image_cleaned.obj")
    voxel_path = Path("outputs/voxels/test_image_voxels.npz")
    ldr_path = Path("outputs/ldr/test_image_output.ldr")
    report_path = Path("outputs/reports/test_image_report.json")
    mesh_inspect_path = Path("outputs/reports/test_image_mesh_inspect.json")
    repair_report_path = Path("outputs/reports/test_image_repair_report.json")
    try:
        image_path.write_bytes(b"fake-image")
        runner = FakeImageToMeshRunner()

        result = run_from_image(
            image_path,
            runner=runner,
            raw_mesh_path=raw_mesh_path,
            cleaned_mesh_path=cleaned_mesh_path,
            voxel_output_path=voxel_path,
            ldr_output_path=ldr_path,
            target_longest_studs=8,
            sample_colors=True,
            optimize=True,
            report_path=report_path,
            raw_mesh_report_path=mesh_inspect_path,
            repair_report_path=repair_report_path,
        )

        brick_lines = [line for line in result.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        mesh_inspect = json.loads(mesh_inspect_path.read_text(encoding="utf-8"))
        repair_report = json.loads(repair_report_path.read_text(encoding="utf-8"))
        assert result == ldr_path
        assert raw_mesh_path.exists()
        assert mesh_inspect["voxelization_ready"] is True
        assert repair_report["mode_requested"] == "basic"
        assert cleaned_mesh_path.exists()
        assert voxel_path.exists()
        assert brick_lines
        assert all(line.split()[1] == "14" for line in brick_lines)
        assert report["optimized"] is True
        assert report["output_brick_count"] == len(brick_lines)
        assert runner.mask_path is None
    finally:
        image_path.unlink(missing_ok=True)
        raw_mesh_path.unlink(missing_ok=True)
        cleaned_mesh_path.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
        mesh_inspect_path.unlink(missing_ok=True)
        repair_report_path.unlink(missing_ok=True)


def test_run_from_image_forwards_mask_to_runner() -> None:
    image_path = Path("outputs/test_input_image.png")
    mask_path = Path("outputs/test_input_mask.png")
    raw_mesh_path = Path("outputs/meshes/test_image_raw.ply")
    cleaned_mesh_path = Path("outputs/meshes/test_image_cleaned.obj")
    voxel_path = Path("outputs/voxels/test_image_voxels.npz")
    ldr_path = Path("outputs/ldr/test_image_output.ldr")
    try:
        image_path.write_bytes(b"fake-image")
        mask_path.write_bytes(b"fake-mask")
        runner = FakeImageToMeshRunner()

        run_from_image(
            image_path,
            runner=runner,
            mask_path=mask_path,
            raw_mesh_path=raw_mesh_path,
            cleaned_mesh_path=cleaned_mesh_path,
            voxel_output_path=voxel_path,
            ldr_output_path=ldr_path,
            target_longest_studs=8,
        )

        assert runner.mask_path == mask_path
    finally:
        image_path.unlink(missing_ok=True)
        mask_path.unlink(missing_ok=True)
        raw_mesh_path.unlink(missing_ok=True)
        cleaned_mesh_path.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)
