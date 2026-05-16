from __future__ import annotations

from pathlib import Path

try:
    import trimesh
except ModuleNotFoundError:  # pragma: no cover
    trimesh = None


def _require_trimesh():
    if trimesh is None:
        raise ModuleNotFoundError("trimesh is required for mesh loading.")
    return trimesh


def scene_to_mesh(scene) -> object:
    tm = _require_trimesh()
    if isinstance(scene, tm.Trimesh):
        return scene
    if isinstance(scene, tm.Scene):
        geometry = scene.to_geometry()
        if isinstance(geometry, tm.Trimesh):
            return geometry
        meshes = [geometry for geometry in scene.dump() if isinstance(geometry, tm.Trimesh)]
        if not meshes:
            raise ValueError("Scene does not contain mesh geometry.")
        return tm.util.concatenate(meshes)
    raise TypeError(f"Expected Trimesh or Scene, got {type(scene)!r}")


def load_mesh(mesh_path: Path):
    tm = _require_trimesh()
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")
    return scene_to_mesh(tm.load(mesh_path))
