from __future__ import annotations

import numpy as np


def fit_mesh_footprint_to_studs(
    mesh,
    *,
    pitch: float,
    target_width_studs: int | None = None,
    target_depth_studs: int | None = None,
) -> tuple[object, dict]:
    """Scale source X/Z dimensions to match a Studio-like target footprint."""
    if pitch <= 0:
        raise ValueError("pitch must be positive.")
    if target_width_studs is not None and target_width_studs <= 0:
        raise ValueError("target_width_studs must be positive.")
    if target_depth_studs is not None and target_depth_studs <= 0:
        raise ValueError("target_depth_studs must be positive.")
    if target_width_studs is None and target_depth_studs is None:
        return mesh, {
            "applied": False,
            "target_width_studs": None,
            "target_depth_studs": None,
            "scale": [1.0, 1.0, 1.0],
        }

    extents = np.asarray(mesh.extents, dtype=np.float64)
    scale_x = 1.0
    scale_z = 1.0
    if target_width_studs is not None:
        if extents[0] <= 0:
            raise ValueError("Mesh has zero X extent.")
        scale_x = (float(target_width_studs) * float(pitch)) / float(extents[0])
    if target_depth_studs is not None:
        if extents[2] <= 0:
            raise ValueError("Mesh has zero Z extent.")
        scale_z = (float(target_depth_studs) * float(pitch)) / float(extents[2])

    scaled = mesh.copy()
    center = np.asarray(scaled.bounds.mean(axis=0), dtype=np.float64)
    transform = np.eye(4)
    transform[:3, 3] = -center
    scaled.apply_transform(transform)
    scaled.apply_scale([scale_x, 1.0, scale_z])
    transform = np.eye(4)
    transform[:3, 3] = center
    scaled.apply_transform(transform)
    return scaled, {
        "applied": True,
        "target_width_studs": target_width_studs,
        "target_depth_studs": target_depth_studs,
        "scale": [round(float(scale_x), 6), 1.0, round(float(scale_z), 6)],
        "pitch": float(pitch),
        "original_extents": [float(value) for value in extents],
        "scaled_extents": [float(value) for value in np.asarray(scaled.extents, dtype=np.float64)],
    }
