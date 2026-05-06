from __future__ import annotations

from pathlib import Path

from makeyourbrick.config import PipelineConfig
from makeyourbrick.brickify.optimizer import brickify_1x1
from makeyourbrick.io.ldr_writer import write_ldr
from makeyourbrick.mesh.solidify import clean_mesh, load_mesh
from makeyourbrick.types import MeshArtifact
from makeyourbrick.voxel.voxelize import compute_pitch, load_voxel_artifact, voxelize_mesh


def run_from_image(image_path: Path, config: PipelineConfig | None = None) -> Path:
    """Run the full pipeline from a single image to an LDR file."""
    _ = image_path
    _ = config or PipelineConfig()
    raise NotImplementedError("Full image-to-LDR pipeline will be wired after Phase 1 modules land.")


def run_from_mesh(mesh_path: Path, config: PipelineConfig | None = None) -> MeshArtifact:
    """Run the non-AI path from an existing mesh artifact."""
    _ = config or PipelineConfig()
    return MeshArtifact(path=mesh_path, source="user", is_watertight=False)


def convert_mesh_to_ldr(
    mesh_path: Path,
    ldr_output_path: Path,
    cleaned_mesh_path: Path,
    voxel_output_path: Path,
    target_longest_studs: int = 24,
    min_pitch: float = 0.005,
    fill: bool = True,
    default_color_id: int = 16,
) -> Path:
    """Convert an existing mesh file to a 1x1-brick LDraw file."""
    mesh = clean_mesh(load_mesh(mesh_path))
    cleaned_mesh_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(cleaned_mesh_path)

    pitch = compute_pitch(mesh, target_longest_studs=target_longest_studs, min_pitch=min_pitch)
    voxelize_mesh(
        mesh,
        voxel_output_path,
        pitch=pitch,
        fill=fill,
        default_color_id=default_color_id,
    )
    occupancy, color_ids, _rgb, _origin, _pitch = load_voxel_artifact(voxel_output_path)
    bricks = brickify_1x1(occupancy, color_ids)
    return write_ldr(bricks, ldr_output_path, title=f"Mesh conversion: {mesh_path.name}")
