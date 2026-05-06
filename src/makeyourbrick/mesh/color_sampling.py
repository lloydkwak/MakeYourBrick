from __future__ import annotations

import numpy as np
from scipy.spatial import cKDTree


def _as_rgb_array(colors: np.ndarray) -> np.ndarray:
    rgb = np.asarray(colors, dtype=np.uint8)
    if rgb.ndim != 2 or rgb.shape[1] < 3:
        raise ValueError("Mesh color array must have shape (n, 3) or (n, 4).")
    return rgb[:, :3]


def _default_rgb_array(count: int, default_rgb: tuple[int, int, int]) -> np.ndarray:
    return np.tile(np.asarray(default_rgb, dtype=np.uint8), (count, 1))


def mesh_has_vertex_colors(mesh) -> bool:
    visual = getattr(mesh, "visual", None)
    if getattr(visual, "kind", None) != "vertex":
        return False
    colors = getattr(visual, "vertex_colors", None)
    return colors is not None and len(colors) == len(mesh.vertices) and len(colors) > 0


def mesh_has_face_colors(mesh) -> bool:
    visual = getattr(mesh, "visual", None)
    if getattr(visual, "kind", None) != "face":
        return False
    colors = getattr(visual, "face_colors", None)
    return colors is not None and len(colors) == len(mesh.faces) and len(colors) > 0


def sample_nearest_vertex_rgb(
    mesh,
    points: np.ndarray,
    default_rgb: tuple[int, int, int] = (160, 165, 169),
) -> np.ndarray:
    if len(points) == 0:
        return np.zeros((0, 3), dtype=np.uint8)
    if not mesh_has_vertex_colors(mesh):
        return _default_rgb_array(len(points), default_rgb)
    colors = _as_rgb_array(mesh.visual.vertex_colors)
    _distance, nearest = cKDTree(np.asarray(mesh.vertices)).query(points)
    return colors[nearest]


def sample_nearest_face_rgb(
    mesh,
    points: np.ndarray,
    default_rgb: tuple[int, int, int] = (160, 165, 169),
) -> np.ndarray:
    if len(points) == 0:
        return np.zeros((0, 3), dtype=np.uint8)
    if not mesh_has_face_colors(mesh):
        return _default_rgb_array(len(points), default_rgb)
    colors = _as_rgb_array(mesh.visual.face_colors)
    _distance, nearest = cKDTree(np.asarray(mesh.triangles_center)).query(points)
    return colors[nearest]


def sample_mesh_rgb(
    mesh,
    points: np.ndarray,
    default_rgb: tuple[int, int, int] = (160, 165, 169),
) -> np.ndarray:
    if mesh_has_vertex_colors(mesh):
        return sample_nearest_vertex_rgb(mesh, points, default_rgb=default_rgb)
    if mesh_has_face_colors(mesh):
        return sample_nearest_face_rgb(mesh, points, default_rgb=default_rgb)
    return _default_rgb_array(len(points), default_rgb)
