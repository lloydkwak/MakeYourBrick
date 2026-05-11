from __future__ import annotations

import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.mesh.orient import infer_up_axis, orient_mesh_to_y_up


def test_infer_up_axis_uses_dominant_longest_axis() -> None:
    z_up = trimesh.creation.box(extents=(1, 1, 4))
    cube = trimesh.creation.box(extents=(1, 1, 1))

    assert infer_up_axis(z_up) == "z"
    assert infer_up_axis(cube) == "y"


def test_orient_mesh_to_y_up_rotates_z_up_mesh() -> None:
    mesh = trimesh.creation.box(extents=(1, 2, 6))

    oriented, report = orient_mesh_to_y_up(mesh, up_axis="z")

    assert report["applied"] is True
    assert report["source_up_axis"] == "z"
    assert oriented.extents[1] == pytest.approx(6)
    assert oriented.extents[2] == pytest.approx(2)


def test_orient_mesh_to_y_up_can_be_disabled() -> None:
    mesh = trimesh.creation.box(extents=(1, 2, 6))

    oriented, report = orient_mesh_to_y_up(mesh, up_axis="none")

    assert oriented is mesh
    assert report["applied"] is False
    assert report["source_up_axis"] == "none"
