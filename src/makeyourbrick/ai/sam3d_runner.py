from __future__ import annotations

import shlex
import subprocess
import os
from pathlib import Path

from makeyourbrick.types import MeshArtifact


class Sam3DRunner:
    """Wrapper around an external facebookresearch/sam-3d-objects checkout."""

    def __init__(
        self,
        repo_path: Path,
        command_template: str | None = None,
        timeout_seconds: int = 3600,
    ) -> None:
        self.repo_path = repo_path
        self.command_template = command_template
        self.timeout_seconds = timeout_seconds

    def _build_command(self, image_path: Path, output_path: Path, mask_path: Path | None = None) -> list[str]:
        if not self.command_template:
            raise NotImplementedError(
                "SAM 3D command template is required. Provide a command containing "
                "{image} and {output} placeholders."
            )
        rendered = self.command_template.format(
            image=str(image_path),
            mask=str(mask_path) if mask_path is not None else "",
            output=str(output_path),
            output_dir=str(output_path.parent),
            repo=str(self.repo_path),
        )
        return shlex.split(rendered, posix=(os.name != "nt"))

    def generate(self, image_path: Path, output_path: Path, mask_path: Path | None = None) -> MeshArtifact:
        if not self.repo_path.exists():
            raise FileNotFoundError(
                f"SAM 3D Objects repo not found at {self.repo_path}. "
                "Clone it under third_party/sam-3d-objects before enabling AI generation."
            )
        if not image_path.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")
        if mask_path is not None and not mask_path.exists():
            raise FileNotFoundError(f"Input mask not found: {mask_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        command = self._build_command(image_path, output_path, mask_path)
        result = subprocess.run(
            command,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "SAM 3D command failed with exit code "
                f"{result.returncode}.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
        if not output_path.exists():
            raise FileNotFoundError(
                f"SAM 3D command completed but did not create expected mesh: {output_path}"
            )
        return MeshArtifact(path=output_path, source="sam3d", is_watertight=False)
