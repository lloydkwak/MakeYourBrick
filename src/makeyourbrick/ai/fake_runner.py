from __future__ import annotations

from pathlib import Path

import numpy as np
import trimesh

from makeyourbrick.types import MeshArtifact


class FakeSamMeshRunner:
    """Deterministic local stand-in for SAM 3D during UI/backend integration."""

    def generate(self, image_path: Path, output_path: Path, mask_path: Path | None = None) -> MeshArtifact:
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        if mask_path is not None and not mask_path.exists():
            raise FileNotFoundError(mask_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mesh = trimesh.creation.box(extents=(1.0, 0.82, 1.18))
        mesh.apply_translation((0.0, 0.0, 0.59))
        mesh.visual.vertex_colors = np.tile(
            np.asarray([[242, 205, 55, 255]], dtype=np.uint8),
            (len(mesh.vertices), 1),
        )
        mesh.export(output_path)
        return MeshArtifact(path=output_path, source="fake-sam-ui-runner", is_watertight=True)
