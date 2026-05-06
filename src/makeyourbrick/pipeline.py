from __future__ import annotations

from pathlib import Path

from makeyourbrick.brickify.colors import load_ldraw_palette
from makeyourbrick.config import PipelineConfig
from makeyourbrick.brickify.optimizer import brickify_1x1, greedy_brickify
from makeyourbrick.brickify.report import build_brick_report, write_brick_report
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
    default_rgb: tuple[int, int, int] | None = None,
    palette_path: Path | None = None,
    optimize: bool = False,
    sample_colors: bool = False,
    report_path: Path | None = None,
) -> Path:
    """Convert an existing mesh file to a 1x1-brick LDraw file."""
    mesh = clean_mesh(load_mesh(mesh_path))
    cleaned_mesh_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(cleaned_mesh_path)

    pitch = compute_pitch(mesh, target_longest_studs=target_longest_studs, min_pitch=min_pitch)
    palette_ids = None
    palette_rgb = None
    if default_rgb is not None or sample_colors:
        palette_ids, palette_rgb = load_ldraw_palette(palette_path or Path("data/ldraw/ldraw_colors.json"))
    voxelize_mesh(
        mesh,
        voxel_output_path,
        pitch=pitch,
        fill=fill,
        default_color_id=default_color_id,
        default_rgb=default_rgb,
        palette_ids=palette_ids,
        palette_rgb=palette_rgb,
        sample_colors=sample_colors,
    )
    occupancy, color_ids, _rgb, _origin, _pitch = load_voxel_artifact(voxel_output_path)
    input_bricks = brickify_1x1(occupancy, color_ids)
    bricks = greedy_brickify(occupancy, color_ids) if optimize else input_bricks
    if report_path is not None:
        write_brick_report(
            build_brick_report(occupancy, input_bricks, bricks, optimized=optimize),
            report_path,
        )
    return write_ldr(bricks, ldr_output_path, title=f"Mesh conversion: {mesh_path.name}")
