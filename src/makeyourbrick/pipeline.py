from __future__ import annotations

from pathlib import Path

from makeyourbrick.ai.sam3d_runner import Sam3DRunner
from makeyourbrick.brickify.colors import load_ldraw_palette
from makeyourbrick.config import PipelineConfig
from makeyourbrick.brickify.optimizer import brick_specs_for_palette, brickify_1x1, greedy_brickify, layered_brickify
from makeyourbrick.brickify.report import build_brick_report, build_stability_report, write_brick_report
from makeyourbrick.io.ldr_writer import BRICK_HEIGHT_LDU, PLATE_HEIGHT_LDU, STUD_LDU, write_ldr
from makeyourbrick.mesh.inspect import inspect_mesh_to_file
from makeyourbrick.mesh.orient import orient_mesh_to_y_up
from makeyourbrick.mesh.repair import repair_mesh, write_repair_report
from makeyourbrick.mesh.scale import fit_mesh_footprint_to_studs
from makeyourbrick.mesh.solidify import clean_mesh, load_mesh
from makeyourbrick.sculpture import (
    SculptureSettings,
    VoxelModel,
    build_contour_shell_targets,
    catalog_for_palette,
    place_layered_bricks,
)
from makeyourbrick.types import MeshArtifact
from makeyourbrick.voxel.sculpture import (
    apply_sculpture_mode,
    apply_voxel_smoothing,
    preprocess_solid_occupancy,
    repair_sculpture_colors,
)
from makeyourbrick.voxel.voxelize import compute_footprint_pitch, compute_pitch, load_voxel_artifact, voxelize_mesh

HEIGHT_UNITS = ("brick", "plate")
SCULPTURE_ENGINES = ("legacy", "layered")
COLOR_STRATEGIES = ("strict", "majority")


def scale_mesh_y(mesh, scale_y: float):
    scaled = mesh.copy()
    scaled.apply_scale([1.0, float(scale_y), 1.0])
    return scaled


def height_unit_ldu(height_unit: str) -> int:
    if height_unit == "brick":
        return BRICK_HEIGHT_LDU
    if height_unit == "plate":
        return PLATE_HEIGHT_LDU
    raise ValueError(f"Unsupported height unit: {height_unit}")


def height_unit_voxel_scale(height_unit: str) -> float:
    return STUD_LDU / height_unit_ldu(height_unit)


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
    base_size_studs: int | None = None,
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
    sculpture_engine: str = "legacy",
    wall_thickness: int = 1,
    base_thickness: int = 0,
    support_spacing: int = 3,
    voxel_smoothing: str = "none",
    infill_density: float = 0.35,
    infill_pattern: str = "lattice",
    optimizer: str = "greedy",
    brick_palette: str = "full",
    height_unit: str = "brick",
    color_strategy: str = "strict",
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
        base_size_studs=base_size_studs,
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
        sculpture_engine=sculpture_engine,
        wall_thickness=wall_thickness,
        base_thickness=base_thickness,
        support_spacing=support_spacing,
        voxel_smoothing=voxel_smoothing,
        infill_density=infill_density,
        infill_pattern=infill_pattern,
        optimizer=optimizer,
        brick_palette=brick_palette,
        height_unit=height_unit,
        color_strategy=color_strategy,
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
    base_size_studs: int | None = None,
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
    sculpture_engine: str = "legacy",
    wall_thickness: int = 1,
    base_thickness: int = 0,
    support_spacing: int = 3,
    voxel_smoothing: str = "none",
    infill_density: float = 0.35,
    infill_pattern: str = "lattice",
    optimizer: str = "greedy",
    brick_palette: str = "full",
    height_unit: str = "brick",
    color_strategy: str = "strict",
    steps_by_layer: bool = False,
) -> Path:
    """Convert an existing mesh file to a 1x1-brick LDraw file."""
    if height_unit not in HEIGHT_UNITS:
        raise ValueError(f"Unsupported height unit: {height_unit}")
    if sculpture_engine not in SCULPTURE_ENGINES:
        raise ValueError(f"Unsupported sculpture engine: {sculpture_engine}")
    if color_strategy not in COLOR_STRATEGIES:
        raise ValueError(f"Unsupported color strategy: {color_strategy}")
    if base_size_studs is not None and base_size_studs <= 0:
        raise ValueError("base_size_studs must be positive.")
    if base_size_studs is not None and (target_width_studs is not None or target_depth_studs is not None):
        raise ValueError("base_size_studs cannot be combined with target_width_studs or target_depth_studs.")
    if height_unit == "plate" and (not optimize or brick_palette != "plates"):
        raise ValueError("Plate height output requires --optimize --brick-palette plates.")
    if repair_mode == "basic" and repair_report_path is None:
        mesh = clean_mesh(load_mesh(mesh_path))
    else:
        mesh, repair_report = repair_mesh(load_mesh(mesh_path), mode=repair_mode)
        if repair_report_path is not None:
            write_repair_report(repair_report, repair_report_path)
    mesh, orientation_report = orient_mesh_to_y_up(mesh, up_axis=up_axis)
    if base_size_studs is not None:
        pitch = compute_footprint_pitch(mesh, base_size_studs=base_size_studs, min_pitch=min_pitch)
        footprint_scale_report = {
            "applied": False,
            "mode": "uniform_base_size",
            "base_size_studs": int(base_size_studs),
            "target_width_studs": None,
            "target_depth_studs": None,
            "scale": [1.0, 1.0, 1.0],
            "pitch": float(pitch),
            "original_extents": [float(value) for value in mesh.extents],
            "scaled_extents": [float(value) for value in mesh.extents],
        }
    else:
        pitch = compute_pitch(mesh, target_longest_studs=target_longest_studs, min_pitch=min_pitch)
        mesh, footprint_scale_report = fit_mesh_footprint_to_studs(
            mesh,
            pitch=pitch,
            target_width_studs=target_width_studs,
            target_depth_studs=target_depth_studs,
        )
    output_height_unit_ldu = height_unit_ldu(height_unit)
    voxel_height_scale = height_unit_voxel_scale(height_unit)
    footprint_scale_report["height_unit"] = height_unit
    footprint_scale_report["height_unit_ldu"] = output_height_unit_ldu
    footprint_scale_report["height_unit_voxel_scale"] = float(voxel_height_scale)
    if voxel_height_scale != 1.0:
        mesh = scale_mesh_y(mesh, voxel_height_scale)
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
    target_model = None
    if sculpture_engine == "layered":
        solid_occupancy = apply_voxel_smoothing(preprocess_solid_occupancy(occupancy), voxel_smoothing)
        solid_color_ids = repair_sculpture_colors(occupancy, solid_occupancy, color_ids)
        solid_model = VoxelModel(
            solid_occupancy,
            solid_color_ids,
            pitch=float(_pitch),
            origin=tuple(float(value) for value in _origin),
            height_unit=height_unit,
        )
        if sculpture_mode == "solid":
            target_model = solid_model
        elif sculpture_mode == "contour-shell":
            targets = build_contour_shell_targets(
                solid_model,
                SculptureSettings(
                    wall_thickness=wall_thickness,
                    base_thickness=base_thickness,
                    support_spacing=support_spacing,
                    brick_palette=brick_palette,
                    height_unit=height_unit,
                ),
            )
            target_model = targets.target
        else:
            raise ValueError("The layered sculpture engine supports sculpture_mode='solid' or 'contour-shell'.")
        occupancy, color_ids = target_model.occupancy, target_model.color_ids
    else:
        occupancy, color_ids = apply_sculpture_mode(
            occupancy,
            color_ids,
            mode=sculpture_mode,
            wall_thickness=wall_thickness,
            base_thickness=base_thickness,
            voxel_smoothing=voxel_smoothing,
            infill_density=infill_density,
            infill_pattern=infill_pattern,
        )
    input_bricks = brickify_1x1(occupancy, color_ids)
    if optimizer not in {"greedy", "layered"}:
        raise ValueError(f"Unsupported optimizer: {optimizer}")
    brick_specs = brick_specs_for_palette(brick_palette)
    if optimize:
        if sculpture_engine == "layered":
            if target_model is None:
                raise RuntimeError("Layered sculpture target was not built.")
            bricks = place_layered_bricks(
                target_model,
                catalog_for_palette(brick_palette),
                color_strategy=color_strategy,
            ).bricks()
        else:
            bricks = (
                layered_brickify(occupancy, color_ids, brick_specs=brick_specs)
                if optimizer == "layered"
                else greedy_brickify(occupancy, color_ids, brick_specs=brick_specs)
            )
    else:
        bricks = input_bricks
    optimizer_name = "reward-sculpture" if optimize and sculpture_engine == "layered" else optimizer
    if report_path is not None:
        write_brick_report(
            build_brick_report(
                occupancy,
                input_bricks,
                bricks,
                optimized=optimize,
                optimizer=optimizer_name if optimize else "none",
                brick_palette=brick_palette if optimize else "none",
                sculpture={
                    "mode": sculpture_mode,
                    "engine": sculpture_engine,
                    "wall_thickness": int(wall_thickness),
                    "base_thickness": int(base_thickness),
                    "support_spacing": int(support_spacing),
                    "voxel_smoothing": voxel_smoothing,
                    "infill_density": float(infill_density),
                    "infill_pattern": infill_pattern,
                    "height_unit": height_unit,
                    "color_strategy": color_strategy,
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
        height_unit_ldu=output_height_unit_ldu,
    )
