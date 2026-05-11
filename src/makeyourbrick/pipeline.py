from __future__ import annotations

from pathlib import Path

from makeyourbrick.ai.sam3d_runner import Sam3DRunner
from makeyourbrick.brickify.colors import load_ldraw_palette
from makeyourbrick.config import PipelineConfig
from makeyourbrick.brickify.optimizer import brickify_1x1, greedy_brickify, layered_brickify
from makeyourbrick.brickify.report import build_brick_report, build_stability_report, write_brick_report
from makeyourbrick.io.ldr_writer import write_ldr
from makeyourbrick.mesh.inspect import inspect_mesh_to_file
from makeyourbrick.mesh.orient import orient_mesh_to_y_up
from makeyourbrick.mesh.repair import repair_mesh, write_repair_report
from makeyourbrick.mesh.scale import fit_mesh_footprint_to_studs
from makeyourbrick.mesh.solidify import clean_mesh, load_mesh
from makeyourbrick.types import MeshArtifact
from makeyourbrick.voxel.sculpture import apply_sculpture_mode
from makeyourbrick.voxel.voxelize import compute_pitch, load_voxel_artifact, voxelize_mesh


def run_from_image(
    image_path: Path,
    config: PipelineConfig | None = None,
    runner: object | None = None,
    mask_path: Path | None = None,
    raw_mesh_path: Path | None = None,
    ldr_output_path: Path | None = None,
    cleaned_mesh_path: Path | None = None,
    voxel_output_path: Path | None = None,
    target_longest_studs: int = 24,
    min_pitch: float = 0.005,
    target_width_studs: int | None = None,
    target_depth_studs: int | None = None,
    fill: bool = True,
    voxelizer: str = "surface",
    ray_fill: str = "wide",
    default_color_id: int = 16,
    default_rgb: tuple[int, int, int] | None = None,
    palette_path: Path | None = None,
    optimize: bool = False,
    sample_colors: bool = False,
    report_path: Path | None = None,
    raw_mesh_report_path: Path | None = None,
    repair_mode: str = "basic",
    repair_report_path: Path | None = None,
    up_axis: str = "auto",
    sculpture_mode: str = "solid",
    wall_thickness: int = 1,
    base_thickness: int = 0,
    voxel_smoothing: str = "none",
    infill_density: float = 0.35,
    optimizer: str = "greedy",
    steps_by_layer: bool = False,
) -> Path:
    """Run the full pipeline from a single image to an LDR file."""
    config = config or PipelineConfig()
    raw_mesh_path = raw_mesh_path or config.paths.raw_mesh
    ldr_output_path = ldr_output_path or config.paths.ldr_output
    cleaned_mesh_path = cleaned_mesh_path or config.paths.watertight_mesh
    voxel_output_path = voxel_output_path or config.paths.voxel_npz
    runner = runner or Sam3DRunner(config.paths.sam3d_repo)

    if mask_path is None:
        artifact = runner.generate(image_path, raw_mesh_path)
    else:
        artifact = runner.generate(image_path, raw_mesh_path, mask_path=mask_path)
    if raw_mesh_report_path is not None:
        inspect_mesh_to_file(artifact.path, raw_mesh_report_path)
    return convert_mesh_to_ldr(
        mesh_path=artifact.path,
        ldr_output_path=ldr_output_path,
        cleaned_mesh_path=cleaned_mesh_path,
        voxel_output_path=voxel_output_path,
        target_longest_studs=target_longest_studs,
        min_pitch=min_pitch,
        target_width_studs=target_width_studs,
        target_depth_studs=target_depth_studs,
        fill=fill,
        voxelizer=voxelizer,
        ray_fill=ray_fill,
        default_color_id=default_color_id,
        default_rgb=default_rgb,
        palette_path=palette_path,
        optimize=optimize,
        sample_colors=sample_colors,
        report_path=report_path,
        repair_mode=repair_mode,
        repair_report_path=repair_report_path,
        up_axis=up_axis,
        sculpture_mode=sculpture_mode,
        wall_thickness=wall_thickness,
        base_thickness=base_thickness,
        voxel_smoothing=voxel_smoothing,
        infill_density=infill_density,
        optimizer=optimizer,
        steps_by_layer=steps_by_layer,
    )


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
    target_width_studs: int | None = None,
    target_depth_studs: int | None = None,
    fill: bool = True,
    voxelizer: str = "surface",
    ray_fill: str = "wide",
    default_color_id: int = 16,
    default_rgb: tuple[int, int, int] | None = None,
    palette_path: Path | None = None,
    optimize: bool = False,
    sample_colors: bool = False,
    report_path: Path | None = None,
    repair_mode: str = "basic",
    repair_report_path: Path | None = None,
    up_axis: str = "auto",
    sculpture_mode: str = "solid",
    wall_thickness: int = 1,
    base_thickness: int = 0,
    voxel_smoothing: str = "none",
    infill_density: float = 0.35,
    optimizer: str = "greedy",
    steps_by_layer: bool = False,
) -> Path:
    """Convert an existing mesh file to a 1x1-brick LDraw file."""
    if repair_mode == "basic" and repair_report_path is None:
        mesh = clean_mesh(load_mesh(mesh_path))
    else:
        mesh, repair_report = repair_mesh(load_mesh(mesh_path), mode=repair_mode)
        if repair_report_path is not None:
            write_repair_report(repair_report, repair_report_path)
    mesh, orientation_report = orient_mesh_to_y_up(mesh, up_axis=up_axis)
    pitch = compute_pitch(mesh, target_longest_studs=target_longest_studs, min_pitch=min_pitch)
    mesh, footprint_scale_report = fit_mesh_footprint_to_studs(
        mesh,
        pitch=pitch,
        target_width_studs=target_width_studs,
        target_depth_studs=target_depth_studs,
    )
    cleaned_mesh_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(cleaned_mesh_path)

    palette_ids = None
    palette_rgb = None
    if default_rgb is not None or sample_colors:
        palette_ids, palette_rgb = load_ldraw_palette(palette_path or Path("data/ldraw/ldraw_colors.json"))
    voxelize_mesh(
        mesh,
        voxel_output_path,
        pitch=pitch,
        fill=fill,
        voxelizer=voxelizer,
        ray_fill=ray_fill,
        default_color_id=default_color_id,
        default_rgb=default_rgb,
        palette_ids=palette_ids,
        palette_rgb=palette_rgb,
        sample_colors=sample_colors,
    )
    occupancy, color_ids, _rgb, _origin, _pitch = load_voxel_artifact(voxel_output_path)
    occupancy, color_ids = apply_sculpture_mode(
        occupancy,
        color_ids,
        mode=sculpture_mode,
        wall_thickness=wall_thickness,
        base_thickness=base_thickness,
        voxel_smoothing=voxel_smoothing,
        infill_density=infill_density,
    )
    input_bricks = brickify_1x1(occupancy, color_ids)
    if optimizer not in {"greedy", "layered"}:
        raise ValueError(f"Unsupported optimizer: {optimizer}")
    if optimize:
        bricks = (
            layered_brickify(occupancy, color_ids)
            if optimizer == "layered"
            else greedy_brickify(occupancy, color_ids)
        )
    else:
        bricks = input_bricks
    if report_path is not None:
        write_brick_report(
            build_brick_report(
                occupancy,
                input_bricks,
                bricks,
                optimized=optimize,
                optimizer=optimizer if optimize else "none",
                sculpture={
                    "mode": sculpture_mode,
                    "wall_thickness": int(wall_thickness),
                    "base_thickness": int(base_thickness),
                    "voxel_smoothing": voxel_smoothing,
                    "infill_density": float(infill_density),
                },
                mesh_orientation=orientation_report,
                footprint_scale=footprint_scale_report,
                stability=build_stability_report(
                    bricks,
                    occupancy.shape,
                    sculpture_mode=sculpture_mode,
                    wall_thickness=wall_thickness,
                    base_thickness=base_thickness,
                ),
            ),
            report_path,
        )
    return write_ldr(
        bricks,
        ldr_output_path,
        title=f"Mesh conversion: {mesh_path.name}",
        step_by_layer=steps_by_layer,
    )
