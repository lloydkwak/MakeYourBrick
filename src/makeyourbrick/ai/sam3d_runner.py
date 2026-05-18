from __future__ import annotations

import shlex
import subprocess
import os
import time
from collections.abc import Callable
from pathlib import Path

from makeyourbrick.ai.gpu_lock import gpu_lock
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
        image_path = image_path.resolve()
        output_path = output_path.resolve()
        mask_path = mask_path.resolve() if mask_path is not None else None
        rendered = self.command_template.format(
            image=str(image_path),
            mask=str(mask_path) if mask_path is not None else "",
            output=str(output_path),
            output_dir=str(output_path.parent),
            repo=str(self.repo_path.resolve()),
        )
        return shlex.split(rendered, posix=(os.name != "nt"))

    def generate(
        self,
        image_path: Path,
        output_path: Path,
        mask_path: Path | None = None,
        on_progress: Callable[[float, str], None] | None = None,
    ) -> MeshArtifact:
        with gpu_lock():
            return self._generate_locked(image_path, output_path, mask_path, on_progress)

    def _generate_locked(
        self,
        image_path: Path,
        output_path: Path,
        mask_path: Path | None = None,
        on_progress: Callable[[float, str], None] | None = None,
    ) -> MeshArtifact:
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
        env = os.environ.copy()
        env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        started_at = time.monotonic()
        log_path = output_path.with_suffix(".sam3d.log")
        log_file = log_path.open("w", encoding="utf-8")
        process = subprocess.Popen(
            command,
            cwd=self.repo_path,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        try:
            while True:
                return_code = process.poll()
                elapsed = time.monotonic() - started_at
                if return_code is not None:
                    break
                if elapsed > self.timeout_seconds:
                    process.kill()
                    process.wait(timeout=10)
                    raise TimeoutError(
                        f"SAM 3D command timed out after {self.timeout_seconds} seconds.\n"
                        f"LOG:\n{_tail_text(log_path)}"
                    )
                if on_progress is not None:
                    minutes = int(elapsed // 60)
                    seconds = int(elapsed % 60)
                    on_progress(
                        elapsed,
                        f"SAM 3D reconstruction running ({minutes:02d}:{seconds:02d} elapsed)",
                    )
                time.sleep(5)
        finally:
            log_file.close()
        if return_code != 0:
            raise RuntimeError(
                "SAM 3D command failed with exit code "
                f"{return_code}.\nLOG:\n{_tail_text(log_path)}"
            )
        if not output_path.exists():
            raise FileNotFoundError(
                f"SAM 3D command completed but did not create expected mesh: {output_path}"
            )
        return MeshArtifact(path=output_path, source="sam3d", is_watertight=False)


def _tail_text(path: Path, max_chars: int = 8000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[-max_chars:]
