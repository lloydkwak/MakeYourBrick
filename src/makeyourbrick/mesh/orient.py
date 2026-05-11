from __future__ import annotations

import math

import numpy as np

UP_AXIS_OPTIONS = ("auto", "none", "x", "y", "z")


def infer_up_axis(mesh, dominance_ratio: float = 1.2) -> str:
    extents = np.asarray(mesh.extents, dtype=float)
    if extents.shape != (3,) or np.any(extents <= 0):
        return "y"
    longest_index = int(np.argmax(extents))
    sorted_extents = np.sort(extents)
    if sorted_extents[-1] < sorted_extents[-2] * dominance_ratio:
        return "y"
    return ("x", "y", "z")[longest_index]


def rotation_to_y_up(source_up_axis: str) -> np.ndarray:
    if source_up_axis == "y":
        return np.eye(4)
    try:
        import trimesh
    except ModuleNotFoundError as error:  # pragma: no cover
        raise ModuleNotFoundError("trimesh is required for mesh orientation.") from error
    if source_up_axis == "z":
        return trimesh.transformations.rotation_matrix(-math.pi / 2, (1, 0, 0))
    if source_up_axis == "x":
        return trimesh.transformations.rotation_matrix(math.pi / 2, (0, 0, 1))
    raise ValueError(f"Unsupported source up axis: {source_up_axis}")


def orient_mesh_to_y_up(mesh, up_axis: str = "auto") -> tuple[object, dict]:
    if up_axis not in UP_AXIS_OPTIONS:
        raise ValueError(f"Unsupported up axis: {up_axis}")
    source_up_axis = infer_up_axis(mesh) if up_axis == "auto" else up_axis
    report = {
        "requested_up_axis": up_axis,
        "source_up_axis": source_up_axis,
        "applied": False,
        "before_extents": [float(value) for value in np.asarray(mesh.extents, dtype=float)],
    }
    if source_up_axis in {"none", "y"}:
        report["after_extents"] = report["before_extents"]
        return mesh, report
    oriented = mesh.copy()
    oriented.apply_transform(rotation_to_y_up(source_up_axis))
    report["applied"] = True
    report["after_extents"] = [float(value) for value in np.asarray(oriented.extents, dtype=float)]
    return oriented, report
