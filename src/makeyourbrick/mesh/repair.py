from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import numpy as np

RepairMode = Literal["none", "basic", "manifold", "convex-hull"]
REPAIR_MODES: tuple[str, ...] = ("none", "basic", "manifold", "convex-hull")


def _mesh_stats(mesh) -> dict:
    volume = getattr(mesh, "volume", None)
    return {
        "vertex_count": int(len(getattr(mesh, "vertices", []))),
        "face_count": int(len(getattr(mesh, "faces", []))),
        "is_watertight": bool(getattr(mesh, "is_watertight", False)),
        "volume": round(float(volume), 6) if volume is not None and np.isfinite(volume) else None,
    }


def _basic_repair(mesh, warnings: list[str]):
    repaired = mesh.copy()
    if hasattr(repaired, "remove_unreferenced_vertices"):
        repaired.remove_unreferenced_vertices()
    if hasattr(repaired, "unique_faces"):
        repaired.update_faces(repaired.unique_faces())
    if hasattr(repaired, "nondegenerate_faces"):
        repaired.update_faces(repaired.nondegenerate_faces())
    elif hasattr(repaired, "remove_degenerate_faces"):
        repaired.remove_degenerate_faces()
    if hasattr(repaired, "merge_vertices"):
        repaired.merge_vertices()
    if hasattr(repaired, "fill_holes"):
        filled = repaired.fill_holes()
        if filled and not repaired.is_watertight:
            warnings.append("Trimesh filled at least one hole, but the mesh is still not watertight.")
    if hasattr(repaired, "fix_normals"):
        repaired.fix_normals()
    if hasattr(repaired, "process"):
        repaired.process(validate=True)
    return repaired


def _manifold_repair(mesh, warnings: list[str]):
    try:
        import manifold3d as mf
    except ModuleNotFoundError:
        warnings.append("manifold3d is not installed; falling back to basic repair.")
        return _basic_repair(mesh, warnings), "basic", True

    try:
        manifold_mesh = mf.Mesh(
            vert_properties=np.asarray(mesh.vertices, dtype=np.float32),
            tri_verts=np.asarray(mesh.faces, dtype=np.uint32),
        )
        manifold = mf.Manifold(manifold_mesh)
        repaired_mesh = manifold.to_mesh()
        vertices = np.asarray(repaired_mesh.vert_properties, dtype=np.float64)[:, :3]
        faces = np.asarray(repaired_mesh.tri_verts, dtype=np.int64)
        repaired = mesh.__class__(vertices=vertices, faces=faces, process=True)
        return repaired, "manifold", False
    except Exception as error:
        warnings.append(f"manifold3d repair failed; falling back to basic repair: {error}")
        return _basic_repair(mesh, warnings), "basic", True


def _convex_hull_repair(mesh, warnings: list[str]):
    cleaned = _basic_repair(mesh, warnings)
    try:
        hull = cleaned.convex_hull
    except Exception as error:
        raise ValueError(f"Convex hull repair failed: {error}") from error
    if hull is None or len(getattr(hull, "faces", [])) == 0:
        raise ValueError("Convex hull repair produced an empty mesh.")
    if hasattr(hull, "process"):
        hull.process(validate=True)
    warnings.append("Convex hull repair replaces concave detail with a watertight outer approximation.")
    return hull


def repair_mesh(mesh, mode: str = "basic") -> tuple[object, dict]:
    if mode not in REPAIR_MODES:
        raise ValueError(f"Unsupported repair mode: {mode}. Expected one of {', '.join(REPAIR_MODES)}.")

    warnings: list[str] = []
    report = {
        "mode_requested": mode,
        "mode_applied": mode,
        "fallback_used": False,
        "status": "completed",
        "before": _mesh_stats(mesh),
        "after": None,
        "warnings": warnings,
        "errors": [],
    }

    try:
        if mode == "none":
            repaired = mesh.copy()
        elif mode == "basic":
            repaired = _basic_repair(mesh, warnings)
        elif mode == "manifold":
            repaired, applied_mode, fallback_used = _manifold_repair(mesh, warnings)
            report["mode_applied"] = applied_mode
            report["fallback_used"] = fallback_used
        else:
            repaired = _convex_hull_repair(mesh, warnings)
    except Exception as error:
        report["status"] = "failed"
        report["errors"].append(str(error))
        raise

    report["after"] = _mesh_stats(repaired)
    if not report["after"]["is_watertight"]:
        warnings.append("Repaired mesh is still not watertight.")
    return repaired, report


def write_repair_report(report: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path
