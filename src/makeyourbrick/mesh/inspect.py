from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

try:
    import trimesh
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps are absent.
    trimesh = None


def _empty_report(mesh_path: Path) -> dict[str, Any]:
    return {
        "path": str(mesh_path),
        "exists": mesh_path.exists(),
        "load_status": "not_started",
        "asset_type": "unknown",
        "geometry_count": 0,
        "vertex_count": 0,
        "face_count": 0,
        "bounds": None,
        "extents": None,
        "is_watertight": False,
        "has_vertex_colors": False,
        "has_face_colors": False,
        "has_texture_hint": False,
        "has_texture_image": False,
        "has_material_diffuse": False,
        "color_source": "none",
        "voxelization_ready": False,
        "warnings": [],
        "errors": [],
    }


def _as_float_list(values: np.ndarray | None) -> list[float] | None:
    if values is None:
        return None
    if not np.all(np.isfinite(values)):
        return None
    return [round(float(value), 6) for value in values.tolist()]


def _inspect_trimesh(mesh: object, report: dict[str, Any]) -> None:
    report["asset_type"] = "triangle_mesh"
    vertices = getattr(mesh, "vertices", np.asarray([]))
    faces = getattr(mesh, "faces", np.asarray([]))
    report["vertex_count"] = int(len(vertices))
    report["face_count"] = int(len(faces))
    bounds = getattr(mesh, "bounds", None)
    extents = getattr(mesh, "extents", None)
    report["bounds"] = [_as_float_list(row) for row in bounds] if bounds is not None else None
    report["extents"] = _as_float_list(extents) if extents is not None else None
    report["is_watertight"] = bool(getattr(mesh, "is_watertight", False))

    visual = getattr(mesh, "visual", None)
    vertex_colors = getattr(visual, "vertex_colors", None)
    face_colors = getattr(visual, "face_colors", None)
    material = getattr(visual, "material", None)
    texture_image = getattr(material, "image", None)
    material_diffuse = getattr(material, "diffuse", None)
    report["has_vertex_colors"] = bool(vertex_colors is not None and len(vertex_colors) == len(vertices))
    report["has_face_colors"] = bool(face_colors is not None and len(face_colors) == len(faces))
    report["has_texture_hint"] = bool(material is not None)
    report["has_texture_image"] = bool(texture_image is not None)
    report["has_material_diffuse"] = bool(material_diffuse is not None)
    if report["has_texture_image"]:
        report["color_source"] = "texture"
    elif report["has_vertex_colors"]:
        report["color_source"] = "vertex"
    elif report["has_face_colors"]:
        report["color_source"] = "face"
    elif report["has_material_diffuse"]:
        report["color_source"] = "material"

    if report["vertex_count"] == 0:
        report["errors"].append("Mesh has no vertices.")
    if report["face_count"] == 0:
        report["errors"].append("Mesh has no triangle faces.")
    if report["extents"] is None or not any(value > 0 for value in report["extents"]):
        report["errors"].append("Mesh bounds are empty or invalid.")
    if not report["is_watertight"]:
        report["warnings"].append("Mesh is not watertight; repair or fill may be required before voxelization.")

    report["voxelization_ready"] = not report["errors"]


def inspect_mesh(mesh_path: Path) -> dict[str, Any]:
    report = _empty_report(mesh_path)
    if not mesh_path.exists():
        report["load_status"] = "failed"
        report["errors"].append(f"Mesh file not found: {mesh_path}")
        return report
    if trimesh is None:
        report["load_status"] = "failed"
        report["errors"].append("trimesh is required for mesh inspection.")
        return report

    try:
        loaded = trimesh.load(mesh_path)
    except Exception as error:
        report["load_status"] = "failed"
        report["errors"].append(str(error))
        return report

    report["load_status"] = "loaded"
    if isinstance(loaded, trimesh.Trimesh):
        _inspect_trimesh(loaded, report)
    elif isinstance(loaded, trimesh.Scene):
        meshes = [geometry for geometry in loaded.dump() if isinstance(geometry, trimesh.Trimesh)]
        report["asset_type"] = "scene"
        report["geometry_count"] = len(loaded.geometry)
        if not meshes:
            report["errors"].append("Scene does not contain triangle mesh geometry.")
            return report
        geometry = loaded.to_geometry()
        if isinstance(geometry, trimesh.Trimesh):
            _inspect_trimesh(geometry, report)
        else:
            _inspect_trimesh(trimesh.util.concatenate(meshes), report)
        report["asset_type"] = "scene"
        report["geometry_count"] = len(meshes)
    elif hasattr(trimesh.points, "PointCloud") and isinstance(loaded, trimesh.points.PointCloud):
        report["asset_type"] = "point_cloud"
        report["vertex_count"] = int(len(getattr(loaded, "vertices", [])))
        report["errors"].append("Point cloud output must be converted to a triangle mesh before voxelization.")
    else:
        report["asset_type"] = type(loaded).__name__
        report["errors"].append(f"Unsupported mesh asset type: {type(loaded).__name__}")
    return report


def write_mesh_inspection(report: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def inspect_mesh_to_file(mesh_path: Path, output_path: Path) -> dict[str, Any]:
    report = inspect_mesh(mesh_path)
    write_mesh_inspection(report, output_path)
    return report
