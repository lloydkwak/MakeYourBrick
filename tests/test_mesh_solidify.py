from __future__ import annotations

from pathlib import Path

import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.mesh.solidify import clean_mesh, load_mesh, scene_to_mesh, solidify_mesh


def test_scene_to_mesh_concatenates_scene_geometry() -> None:
    scene = trimesh.Scene()
    scene.add_geometry(trimesh.creation.box(extents=(1, 1, 1)))
    scene.add_geometry(trimesh.creation.box(extents=(1, 2, 1)))

    mesh = scene_to_mesh(scene)

    assert isinstance(mesh, trimesh.Trimesh)
    assert len(mesh.faces) > 0


def test_clean_mesh_preserves_valid_box_geometry() -> None:
    mesh = trimesh.creation.box(extents=(1, 1, 1))

    cleaned = clean_mesh(mesh)

    assert isinstance(cleaned, trimesh.Trimesh)
    assert cleaned.is_watertight
    assert len(cleaned.faces) > 0


def test_solidify_mesh_exports_cleaned_artifact() -> None:
    input_path = Path("outputs/meshes/test_solidify_input.stl")
    output_path = Path("outputs/meshes/test_solidify_output.glb")
    try:
        input_path.parent.mkdir(parents=True, exist_ok=True)
        trimesh.creation.box(extents=(1, 1, 1)).export(input_path)

        artifact = solidify_mesh(input_path, output_path)
        reloaded = load_mesh(output_path)

        assert artifact.path == output_path
        assert artifact.is_watertight
        assert reloaded.is_watertight
    finally:
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)

