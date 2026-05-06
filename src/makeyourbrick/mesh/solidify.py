from __future__ import annotations

from pathlib import Path

try:
    import trimesh
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps are absent.
    trimesh = None

from makeyourbrick.types import MeshArtifact


def _require_trimesh():
    if trimesh is None:
        raise ModuleNotFoundError(
            "trimesh is required for mesh loading. Install project dependencies first."
        )
    return trimesh


def scene_to_mesh(scene) -> object:
    tm = _require_trimesh()
    if isinstance(scene, tm.Trimesh):
        return scene
    if isinstance(scene, tm.Scene):
        meshes = [geometry for geometry in scene.geometry.values() if isinstance(geometry, tm.Trimesh)]
        if not meshes:
            raise ValueError("Scene does not contain mesh geometry.")
        return tm.util.concatenate(meshes)
    raise TypeError(f"Expected Trimesh or Scene, got {type(scene)!r}")


def load_mesh(mesh_path: Path):
    tm = _require_trimesh()
    if not mesh_path.exists():
        raise FileNotFoundError(f"Mesh file not found: {mesh_path}")
    loaded = tm.load(mesh_path)
    return scene_to_mesh(loaded)


def clean_mesh(mesh):
    mesh = mesh.copy()
    if hasattr(mesh, "remove_unreferenced_vertices"):
        mesh.remove_unreferenced_vertices()
    if hasattr(mesh, "unique_faces"):
        mesh.update_faces(mesh.unique_faces())
    if hasattr(mesh, "nondegenerate_faces"):
        mesh.update_faces(mesh.nondegenerate_faces())
    if hasattr(mesh, "process"):
        mesh.process(validate=True)
    return mesh


def solidify_mesh(input_path: Path, output_path: Path) -> MeshArtifact:
    mesh = load_mesh(input_path)
    mesh = clean_mesh(mesh)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(output_path)
    return MeshArtifact(path=output_path, source=str(input_path), is_watertight=bool(mesh.is_watertight))
