from __future__ import annotations

import json
from pathlib import Path

import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.mesh.repair import repair_mesh, write_repair_report


def make_open_box():
    mesh = trimesh.creation.box(extents=(1, 1, 1))
    mesh.update_faces([index for index in range(len(mesh.faces)) if index != 0])
    mesh.remove_unreferenced_vertices()
    return mesh


def test_none_repair_preserves_open_mesh_status() -> None:
    repaired, report = repair_mesh(make_open_box(), mode="none")

    assert report["mode_requested"] == "none"
    assert report["mode_applied"] == "none"
    assert report["before"]["is_watertight"] is False
    assert report["after"]["is_watertight"] is False
    assert repaired.is_watertight is False


def test_basic_repair_fills_simple_hole_and_writes_report() -> None:
    report_path = Path("outputs/reports/test_basic_repair.json")
    try:
        repaired, report = repair_mesh(make_open_box(), mode="basic")
        write_repair_report(report, report_path)

        saved = json.loads(report_path.read_text(encoding="utf-8"))
        assert repaired.is_watertight is True
        assert report["before"]["is_watertight"] is False
        assert saved["after"]["is_watertight"] is True
        assert saved["errors"] == []
    finally:
        report_path.unlink(missing_ok=True)


def test_convex_hull_repair_produces_watertight_outer_approximation() -> None:
    repaired, report = repair_mesh(make_open_box(), mode="convex-hull")

    assert repaired.is_watertight is True
    assert report["mode_requested"] == "convex-hull"
    assert report["after"]["is_watertight"] is True
    assert any("outer approximation" in warning for warning in report["warnings"])


def test_manifold_mode_is_explicit_even_when_falling_back() -> None:
    repaired, report = repair_mesh(make_open_box(), mode="manifold")

    assert repaired.faces.shape[0] > 0
    assert report["mode_requested"] == "manifold"
    assert report["mode_applied"] in {"manifold", "basic"}
    if report["fallback_used"]:
        assert any("falling back to basic repair" in warning for warning in report["warnings"])


def test_repair_rejects_unknown_mode() -> None:
    with pytest.raises(ValueError, match="Unsupported repair mode"):
        repair_mesh(make_open_box(), mode="unknown")
