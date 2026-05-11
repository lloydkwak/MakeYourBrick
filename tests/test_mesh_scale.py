from __future__ import annotations

import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.mesh.scale import fit_mesh_footprint_to_studs


def test_fit_mesh_footprint_to_studs_scales_xz_around_center() -> None:
    mesh = trimesh.creation.box(extents=(2, 4, 1))

    scaled, report = fit_mesh_footprint_to_studs(
        mesh,
        pitch=0.5,
        target_width_studs=8,
        target_depth_studs=6,
    )

    assert report["applied"] is True
    assert report["scale"] == [2.0, 1.0, 3.0]
    assert scaled.extents[0] == pytest.approx(4.0)
    assert scaled.extents[1] == pytest.approx(4.0)
    assert scaled.extents[2] == pytest.approx(3.0)
    assert scaled.centroid[0] == pytest.approx(mesh.centroid[0])
    assert scaled.centroid[2] == pytest.approx(mesh.centroid[2])


def test_fit_mesh_footprint_to_studs_is_noop_without_targets() -> None:
    mesh = trimesh.creation.box(extents=(2, 4, 1))

    scaled, report = fit_mesh_footprint_to_studs(mesh, pitch=0.5)

    assert scaled is mesh
    assert report["applied"] is False
