from __future__ import annotations

from pathlib import Path

import trimesh

from makeyourbrick.types import MeshArtifact


def load_mesh(mesh_path: Path) -> trimesh.Trimesh:
    loaded = trimesh.load(mesh_path, force="mesh")
    if not isinstance(loaded, trimesh.Trimesh):
        raise TypeError(f"Expected a Trimesh object, got {type(loaded)!r}")
    return loaded


def solidify_mesh(input_path: Path, output_path: Path) -> MeshArtifact:
    mesh = load_mesh(input_path)
    mesh.remove_unreferenced_vertices()
    mesh.update_faces(mesh.unique_faces())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(output_path)
    return MeshArtifact(path=output_path, source=str(input_path), is_watertight=bool(mesh.is_watertight))

