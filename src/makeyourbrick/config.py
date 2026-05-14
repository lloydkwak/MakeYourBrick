from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PipelinePaths:
    sam3d_repo: Path = Path("third_party/sam-3d-objects")
    input_image: Path = Path("data/input_images/sample.png")
    raw_mesh: Path = Path("outputs/meshes/raw_model.obj")
    watertight_mesh: Path = Path("outputs/meshes/cleaned_model.obj")
    voxel_npz: Path = Path("outputs/voxels/model_voxels.npz")
    ldr_output: Path = Path("outputs/ldr/lego_output.ldr")
    ldraw_colors: Path = Path("data/ldraw/ldraw_colors.json")


@dataclass(frozen=True)
class VoxelConfig:
    target_longest_studs: int = 48
    min_pitch: float = 0.005
    fill: bool = True


@dataclass(frozen=True)
class PipelineConfig:
    paths: PipelinePaths = PipelinePaths()
    voxel: VoxelConfig = VoxelConfig()
