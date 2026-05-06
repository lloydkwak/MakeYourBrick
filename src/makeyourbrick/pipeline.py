from __future__ import annotations

from pathlib import Path

from makeyourbrick.config import PipelineConfig
from makeyourbrick.types import MeshArtifact


def run_from_image(image_path: Path, config: PipelineConfig | None = None) -> Path:
    """Run the full pipeline from a single image to an LDR file."""
    _ = image_path
    _ = config or PipelineConfig()
    raise NotImplementedError("Full image-to-LDR pipeline will be wired after Phase 1 modules land.")


def run_from_mesh(mesh_path: Path, config: PipelineConfig | None = None) -> MeshArtifact:
    """Run the non-AI path from an existing mesh artifact."""
    _ = config or PipelineConfig()
    return MeshArtifact(path=mesh_path, source="user", is_watertight=False)

