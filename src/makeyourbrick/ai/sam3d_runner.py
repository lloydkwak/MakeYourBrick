from __future__ import annotations

from pathlib import Path

from makeyourbrick.types import MeshArtifact


class Sam3DRunner:
    """Wrapper around an external facebookresearch/sam-3d-objects checkout."""

    def __init__(self, repo_path: Path) -> None:
        self.repo_path = repo_path

    def generate(self, image_path: Path, output_path: Path) -> MeshArtifact:
        if not self.repo_path.exists():
            raise FileNotFoundError(
                f"SAM 3D Objects repo not found at {self.repo_path}. "
                "Clone it under third_party/sam-3d-objects before enabling AI generation."
            )
        if not image_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")
        raise NotImplementedError("SAM 3D subprocess/API integration is scheduled for Phase 5.")

