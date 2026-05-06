from __future__ import annotations

import sys
from pathlib import Path

import pytest

from makeyourbrick.ai.sam3d_runner import Sam3DRunner


def test_sam3d_runner_rejects_missing_repo() -> None:
    runner = Sam3DRunner(Path("does/not/exist"), command_template="python fake.py")

    with pytest.raises(FileNotFoundError, match="SAM 3D Objects repo"):
        runner.generate(Path("data/input_images/missing.png"), Path("outputs/meshes/raw_model.glb"))


def test_sam3d_runner_rejects_missing_image() -> None:
    runner = Sam3DRunner(Path("."), command_template="python fake.py")

    with pytest.raises(FileNotFoundError, match="Input image"):
        runner.generate(Path("data/input_images/missing.png"), Path("outputs/meshes/raw_model.glb"))


def test_sam3d_runner_requires_command_template() -> None:
    image_path = Path("outputs/test_sam_input.png")
    try:
        image_path.write_bytes(b"fake")
        runner = Sam3DRunner(Path("."))

        with pytest.raises(NotImplementedError, match="command template"):
            runner.generate(image_path, Path("outputs/meshes/raw_model.glb"))
    finally:
        image_path.unlink(missing_ok=True)


def test_sam3d_runner_executes_command_and_returns_mesh_artifact() -> None:
    image_path = Path("outputs/test_sam_input.png")
    output_path = Path("outputs/meshes/test_sam_output.glb")
    try:
        image_path.write_bytes(b"fake")
        command = f"{sys.executable} tests/fake_sam3d_command.py --output {{output}}"
        runner = Sam3DRunner(Path("."), command_template=command, timeout_seconds=10)

        artifact = runner.generate(image_path, output_path)

        assert artifact.path == output_path
        assert artifact.source == "sam3d"
        assert output_path.read_bytes() == b"mesh"
    finally:
        image_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def test_sam3d_runner_reports_failed_command() -> None:
    image_path = Path("outputs/test_sam_input.png")
    try:
        image_path.write_bytes(b"fake")
        runner = Sam3DRunner(
            Path("."),
            command_template=f"{sys.executable} tests/fake_sam3d_command.py --output {{output}} --exit-code 3",
            timeout_seconds=10,
        )

        with pytest.raises(RuntimeError, match="exit code 3"):
            runner.generate(image_path, Path("outputs/meshes/test_sam_output.glb"))
    finally:
        image_path.unlink(missing_ok=True)
