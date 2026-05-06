from __future__ import annotations

import numpy as np
import pytest

trimesh = pytest.importorskip("trimesh")

from makeyourbrick.mesh.color_sampling import (
    mesh_has_face_colors,
    mesh_has_vertex_colors,
    sample_mesh_rgb,
    sample_nearest_face_rgb,
    sample_nearest_vertex_rgb,
)


def test_sample_nearest_vertex_rgb_uses_closest_vertex_color() -> None:
    mesh = trimesh.Trimesh(
        vertices=np.asarray([[0, 0, 0], [10, 0, 0]], dtype=float),
        faces=np.asarray([[0, 1, 1]]),
        process=False,
    )
    mesh.visual.vertex_colors = np.asarray([[255, 0, 0, 255], [0, 0, 255, 255]], dtype=np.uint8)

    rgb = sample_nearest_vertex_rgb(mesh, np.asarray([[0.1, 0, 0], [9.9, 0, 0]], dtype=float))

    np.testing.assert_array_equal(rgb, np.asarray([[255, 0, 0], [0, 0, 255]], dtype=np.uint8))


def test_sample_nearest_face_rgb_uses_closest_triangle_center_color() -> None:
    mesh = trimesh.Trimesh(
        vertices=np.asarray(
            [
                [0, 0, 0],
                [1, 0, 0],
                [0, 1, 0],
                [10, 0, 0],
                [11, 0, 0],
                [10, 1, 0],
            ],
            dtype=float,
        ),
        faces=np.asarray([[0, 1, 2], [3, 4, 5]]),
        process=False,
    )
    mesh.visual.face_colors = np.asarray([[255, 0, 0, 255], [0, 255, 0, 255]], dtype=np.uint8)

    rgb = sample_nearest_face_rgb(mesh, np.asarray([[0.3, 0.3, 0], [10.3, 0.3, 0]], dtype=float))

    np.testing.assert_array_equal(rgb, np.asarray([[255, 0, 0], [0, 255, 0]], dtype=np.uint8))


def test_sample_mesh_rgb_uses_vertex_color_visuals() -> None:
    mesh = trimesh.creation.box(extents=(1, 1, 1))
    mesh.visual.vertex_colors = np.tile(np.asarray([[255, 0, 0, 255]], dtype=np.uint8), (len(mesh.vertices), 1))

    rgb = sample_mesh_rgb(mesh, np.asarray([[0, 0, 0]], dtype=float))

    assert mesh_has_vertex_colors(mesh)
    assert not mesh_has_face_colors(mesh)
    np.testing.assert_array_equal(rgb, np.asarray([[255, 0, 0]], dtype=np.uint8))


def test_sample_mesh_rgb_falls_back_to_default_when_mesh_has_no_colors() -> None:
    mesh = trimesh.creation.box(extents=(1, 1, 1))

    rgb = sample_mesh_rgb(mesh, np.asarray([[0, 0, 0], [1, 1, 1]], dtype=float), default_rgb=(1, 2, 3))

    np.testing.assert_array_equal(rgb, np.asarray([[1, 2, 3], [1, 2, 3]], dtype=np.uint8))
