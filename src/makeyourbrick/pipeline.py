from __future__ import annotations

from pathlib import Path

from makeyourbrick.ai.sam3d_runner import Sam3DRunner
from makeyourbrick.brickify.optimizer import brickify_1x1
from makeyourbrick.brickify.report import build_brick_report, build_stability_report, write_brick_report
from makeyourbrick.config import PipelineConfig
from makeyourbrick.io.ldr_writer import BRICK_HEIGHT_LDU, STUD_LDU, write_ldr
from makeyourbrick.mesh.inspect import inspect_mesh_to_file
from makeyourbrick.mesh.orient import orient_mesh_to_y_up
from makeyourbrick.mesh.solidify import load_mesh
from makeyourbrick.sculpture import (
    SculptureSettings,
    VoxelModel,
    build_contour_shell_targets,
    catalog_for_palette,
    place_layered_bricks,
)
from makeyourbrick.voxel.sculpture import apply_voxel_smoothing, preprocess_solid_occupancy, repair_sculpture_colors
from makeyourbrick.voxel.voxelize import compute_footprint_pitch, load_voxel_artifact, voxelize_mesh

DEFAULT_BASE_SIZE_STUDS = 32
DEFAULT_WALL_THICKNESS = 2
DEFAULT_BASE_THICKNESS = 3


def _scale_mesh_y_for_brick_height(mesh):
    scaled = mesh.copy()
    scaled.apply_scale([1.0, STUD_LDU / BRICK_HEIGHT_LDU, 1.0])
    return scaled


def run_from_image(
    image_path: Path,
    *,
    runner: object | None = None,
    mask_path: Path | None = None,
    raw_mesh_path: Path | None = None,
    ldr_output_path: Path | None = None,
    voxel_output_path: Path | None = None,
    report_path: Path | None = None,
    raw_mesh_report_path: Path | None = None,
    base_size_studs: int = DEFAULT_BASE_SIZE_STUDS,
    wall_thickness: int = DEFAULT_WALL_THICKNESS,
    base_thickness: int = DEFAULT_BASE_THICKNESS,
    up_axis: str = "auto",
    min_pitch: float = 0.005,
) -> Path:
    config = PipelineConfig()
    raw_mesh_path = raw_mesh_path or config.paths.raw_mesh
    ldr_output_path = ldr_output_path or config.paths.ldr_output
    voxel_output_path = voxel_output_path or config.paths.voxel_npz
    runner = runner or Sam3DRunner(config.paths.sam3d_repo)
    artifact = runner.generate(image_path, raw_mesh_path, mask_path=mask_path)
    if raw_mesh_report_path is not None:
        inspect_mesh_to_file(artifact.path, raw_mesh_report_path)
    return convert_mesh_to_ldr(
        mesh_path=artifact.path,
        ldr_output_path=ldr_output_path,
        voxel_output_path=voxel_output_path,
        report_path=report_path,
        base_size_studs=base_size_studs,
        wall_thickness=wall_thickness,
        base_thickness=base_thickness,
        up_axis=up_axis,
        min_pitch=min_pitch,
    )


def convert_mesh_to_ldr(
    *,
    mesh_path: Path,
    ldr_output_path: Path,
    voxel_output_path: Path,
    report_path: Path | None = None,
    debug_target_ldr_path: Path | None = None,
    base_size_studs: int = DEFAULT_BASE_SIZE_STUDS,
    wall_thickness: int = DEFAULT_WALL_THICKNESS,
    base_thickness: int = DEFAULT_BASE_THICKNESS,
    up_axis: str = "auto",
    min_pitch: float = 0.005,
    steps_by_layer: bool = True,
) -> Path:
    mesh = load_mesh(mesh_path)
    mesh, orientation_report = orient_mesh_to_y_up(mesh, up_axis=up_axis)
    pitch = compute_footprint_pitch(mesh, base_size_studs=base_size_studs, min_pitch=min_pitch)
    mesh = _scale_mesh_y_for_brick_height(mesh)
    footprint_report = {
        "mode": "uniform_base_size",
        "base_size_studs": int(base_size_studs),
        "pitch": float(pitch),
        "height_unit": "brick",
        "height_unit_ldu": BRICK_HEIGHT_LDU,
        "height_unit_voxel_scale": STUD_LDU / BRICK_HEIGHT_LDU,
    }
    voxel_artifact = voxelize_mesh(mesh, voxel_output_path, pitch=pitch)
    occupancy, color_ids, _rgb, origin, loaded_pitch = load_voxel_artifact(voxel_output_path)
    solid_occupancy = apply_voxel_smoothing(preprocess_solid_occupancy(occupancy), "polished")
    solid_colors = repair_sculpture_colors(occupancy, solid_occupancy, color_ids)
    solid_model = VoxelModel(
        solid_occupancy,
        solid_colors,
        pitch=float(loaded_pitch),
        origin=tuple(float(value) for value in origin),
    )
    targets = build_contour_shell_targets(
        solid_model,
        SculptureSettings(wall_thickness=wall_thickness, base_thickness=base_thickness),
    )
    target_model = targets.target
    input_bricks = brickify_1x1(target_model.occupancy, target_model.color_ids)
    if debug_target_ldr_path is not None:
        write_ldr(
            input_bricks,
            debug_target_ldr_path,
            title=f"1x1 target debug: {mesh_path.name}",
            step_by_layer=steps_by_layer,
            height_unit_ldu=BRICK_HEIGHT_LDU,
        )
    placed_model = place_layered_bricks(target_model, catalog_for_palette("studio"))
    bricks = placed_model.bricks()

    if report_path is not None:
        write_brick_report(
            build_brick_report(
                target_model.occupancy,
                input_bricks,
                bricks,
                optimized=True,
                optimizer="studio-layered",
                brick_palette="studio",
                sculpture={
                    "mode": "contour-shell",
                    "wall_thickness": int(wall_thickness),
                    "base_thickness": int(base_thickness),
                    "color_strategy": "layer",
                    "voxelizer": voxel_artifact.voxelizer,
                },
                mesh_orientation=orientation_report,
                footprint_scale=footprint_report,
                stability=build_stability_report(
                    bricks,
                    target_model.shape,
                    sculpture_mode="contour-shell",
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
        height_unit_ldu=BRICK_HEIGHT_LDU,
    )
