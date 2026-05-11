from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

import numpy as np
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


def test_mesh_to_ldr_cli_quantizes_rgb_to_ldraw_color_id() -> None:
    input_mesh = Path("outputs/meshes/test_cli_rgb_box.stl")
    cleaned_mesh = Path("outputs/meshes/test_cli_rgb_cleaned.glb")
    voxel_path = Path("outputs/voxels/test_cli_rgb_voxels.npz")
    ldr_path = Path("outputs/ldr/test_cli_rgb_mesh.ldr")
    try:
        input_mesh.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(input_mesh)

        subprocess.run(
            [
                sys.executable,
                "scripts/mesh_to_ldr.py",
                "--mesh",
                str(input_mesh),
                "--target-studs",
                "8",
                "--rgb",
                "242",
                "205",
                "55",
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

        brick_lines = [line for line in ldr_path.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
        assert brick_lines
        assert all(line.split()[1] == "14" for line in brick_lines)
    finally:
        input_mesh.unlink(missing_ok=True)
        cleaned_mesh.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)


def test_mesh_to_ldr_cli_can_write_optimized_output() -> None:
    input_mesh = Path("outputs/meshes/test_cli_optimized_box.stl")
    cleaned_mesh = Path("outputs/meshes/test_cli_optimized_cleaned.glb")
    voxel_path = Path("outputs/voxels/test_cli_optimized_voxels.npz")
    ldr_path = Path("outputs/ldr/test_cli_optimized_mesh.ldr")
    try:
        input_mesh.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(input_mesh)

        subprocess.run(
            [
                sys.executable,
                "scripts/mesh_to_ldr.py",
                "--mesh",
                str(input_mesh),
                "--target-studs",
                "8",
                "--optimize",
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

        brick_lines = [line for line in ldr_path.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
        assert brick_lines
        assert len(brick_lines) < 729
        assert any(line.endswith(("3001.dat", "3006.dat", "3007.dat", "2456.dat")) for line in brick_lines)
    finally:
        input_mesh.unlink(missing_ok=True)
        cleaned_mesh.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)


def test_mesh_to_ldr_cli_can_write_optimizer_report() -> None:
    input_mesh = Path("outputs/meshes/test_cli_report_box.stl")
    cleaned_mesh = Path("outputs/meshes/test_cli_report_cleaned.glb")
    voxel_path = Path("outputs/voxels/test_cli_report_voxels.npz")
    ldr_path = Path("outputs/ldr/test_cli_report_mesh.ldr")
    report_path = Path("outputs/reports/test_cli_report.json")
    repair_report_path = Path("outputs/reports/test_cli_repair_report.json")
    try:
        input_mesh.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(input_mesh)

        subprocess.run(
            [
                sys.executable,
                "scripts/mesh_to_ldr.py",
                "--mesh",
                str(input_mesh),
                "--target-studs",
                "8",
                "--optimize",
                "--cleaned-mesh",
                str(cleaned_mesh),
                "--voxels",
                str(voxel_path),
                "--output",
                str(ldr_path),
                "--report",
                str(report_path),
                "--repair-report",
                str(repair_report_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        repair_report = json.loads(repair_report_path.read_text(encoding="utf-8"))
        assert report["optimized"] is True
        assert report["optimizer"] == "greedy"
        assert report["sculpture"]["mode"] == "solid"
        assert report["stability"]["layer_count"] > 0
        assert repair_report["mode_requested"] == "basic"
        assert repair_report["after"]["is_watertight"] is True
        assert report["input_brick_count"] == 729
        assert report["output_brick_count"] < report["input_brick_count"]
        assert report["part_counts"]
    finally:
        input_mesh.unlink(missing_ok=True)
        cleaned_mesh.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
        repair_report_path.unlink(missing_ok=True)


def test_mesh_to_ldr_cli_supports_sculpture_shell_layered_steps() -> None:
    input_mesh = Path("outputs/meshes/test_cli_sculpture_box.stl")
    cleaned_mesh = Path("outputs/meshes/test_cli_sculpture_cleaned.glb")
    voxel_path = Path("outputs/voxels/test_cli_sculpture_voxels.npz")
    ldr_path = Path("outputs/ldr/test_cli_sculpture_mesh.ldr")
    report_path = Path("outputs/reports/test_cli_sculpture_report.json")
    try:
        input_mesh.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(input_mesh)

        subprocess.run(
            [
                sys.executable,
                "scripts/mesh_to_ldr.py",
                "--mesh",
                str(input_mesh),
                "--target-studs",
                "8",
                "--optimize",
                "--optimizer",
                "layered",
                "--sculpture-mode",
                "shell",
                "--wall-thickness",
                "1",
                "--base-thickness",
                "1",
                "--steps-by-layer",
                "--cleaned-mesh",
                str(cleaned_mesh),
                "--voxels",
                str(voxel_path),
                "--output",
                str(ldr_path),
                "--report",
                str(report_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert "0 STEP" in ldr_path.read_text(encoding="utf-8")
        assert report["optimizer"] == "layered"
        assert report["sculpture"]["mode"] == "shell"
        assert report["sculpture"]["base_thickness"] == 1
        assert report["stability"]["average_support_ratio"] >= 0
    finally:
        input_mesh.unlink(missing_ok=True)
        cleaned_mesh.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)


def test_mesh_to_ldr_cli_can_sample_mesh_colors_and_write_report() -> None:
    input_mesh = Path("outputs/meshes/test_cli_sampled_color.ply")
    cleaned_mesh = Path("outputs/meshes/test_cli_sampled_color_cleaned.glb")
    voxel_path = Path("outputs/voxels/test_cli_sampled_color_voxels.npz")
    ldr_path = Path("outputs/ldr/test_cli_sampled_color.ldr")
    report_path = Path("outputs/reports/test_cli_sampled_color_report.json")
    try:
        input_mesh.parent.mkdir(parents=True, exist_ok=True)
        mesh = trimesh.creation.box(extents=(1, 1, 1))
        mesh.visual.vertex_colors = np.tile(
            np.asarray([[242, 205, 55, 255]], dtype=np.uint8),
            (len(mesh.vertices), 1),
        )
        mesh.export(input_mesh)

        subprocess.run(
            [
                sys.executable,
                "scripts/mesh_to_ldr.py",
                "--mesh",
                str(input_mesh),
                "--target-studs",
                "8",
                "--sample-colors",
                "--optimize",
                "--cleaned-mesh",
                str(cleaned_mesh),
                "--voxels",
                str(voxel_path),
                "--output",
                str(ldr_path),
                "--report",
                str(report_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        brick_lines = [line for line in ldr_path.read_text(encoding="utf-8").splitlines() if line.startswith("1 ")]
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert brick_lines
        assert all(line.split()[1] == "14" for line in brick_lines)
        assert report["optimized"] is True
        assert report["output_brick_count"] == len(brick_lines)
    finally:
        input_mesh.unlink(missing_ok=True)
        cleaned_mesh.unlink(missing_ok=True)
        voxel_path.unlink(missing_ok=True)
        ldr_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
