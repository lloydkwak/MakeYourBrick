from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelinePaths:
    sam3d_repo: Path = Path("third_party/sam-3d-objects")
    input_image: Path = Path("data/input_images/sample.png")
    raw_mesh: Path = Path("outputs/meshes/raw_model.obj")
    voxel_npz: Path = Path("outputs/voxels/model_voxels.npz")
    ldr_output: Path = Path("outputs/ldr/lego_output.ldr")


@dataclass(frozen=True)
class PipelineConfig:
    paths: PipelinePaths = PipelinePaths()
