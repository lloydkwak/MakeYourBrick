from __future__ import annotations

import json
from pathlib import Path

from makeyourbrick.pipeline import convert_mesh_to_ldr

SAMPLE_NAMES = ("sphere", "bust", "object")


def _require_trimesh():
    try:
        import trimesh
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError("trimesh is required for mesh sample comparison.") from error
    return trimesh


def create_sample_mesh(name: str):
    trimesh = _require_trimesh()
    if name == "sphere":
        return trimesh.creation.icosphere(subdivisions=2, radius=0.5)
    if name == "bust":
        head = trimesh.creation.icosphere(subdivisions=2, radius=0.32)
        head.apply_translation((0.0, 0.42, 0.0))
        torso = trimesh.creation.capsule(radius=0.28, height=0.75, count=[16, 16])
        torso.apply_translation((0.0, -0.1, 0.0))
        return trimesh.util.concatenate([head, torso])
    if name == "object":
        body = trimesh.creation.box(extents=(0.9, 0.55, 0.55))
        handle = trimesh.creation.cylinder(radius=0.18, height=0.55, sections=16)
        handle.apply_transform(trimesh.transformations.rotation_matrix(1.57079632679, (0, 1, 0)))
        handle.apply_translation((0.55, 0.0, 0.0))
        return trimesh.util.concatenate([body, handle])
    raise ValueError(f"Unsupported sample mesh: {name}")


def write_sample_mesh(name: str, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    create_sample_mesh(name).export(output_path)
    return output_path


def compare_mesh_samples(
    output_dir: Path,
    *,
    samples: tuple[str, ...] = SAMPLE_NAMES,
    target_studs: int = 8,
    sculpture_mode: str = "shell",
    wall_thickness: int = 1,
    base_thickness: int = 1,
    voxel_smoothing: str = "none",
    infill_density: float = 0.35,
    optimizer: str = "layered",
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    sample_reports = []
    for name in samples:
        mesh_path = write_sample_mesh(name, output_dir / "meshes" / f"{name}.stl")
        cleaned_mesh_path = output_dir / "cleaned" / f"{name}.glb"
        voxel_path = output_dir / "voxels" / f"{name}.npz"
        ldr_path = output_dir / "ldr" / f"{name}.ldr"
        report_path = output_dir / "reports" / f"{name}.json"
        convert_mesh_to_ldr(
            mesh_path=mesh_path,
            ldr_output_path=ldr_path,
            cleaned_mesh_path=cleaned_mesh_path,
            voxel_output_path=voxel_path,
            target_longest_studs=target_studs,
            optimize=True,
            optimizer=optimizer,
            sculpture_mode=sculpture_mode,
            wall_thickness=wall_thickness,
            base_thickness=base_thickness,
            voxel_smoothing=voxel_smoothing,
            infill_density=infill_density,
            steps_by_layer=True,
            report_path=report_path,
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        sample_reports.append(
            {
                "sample": name,
                "mesh_path": str(mesh_path),
                "ldr_path": str(ldr_path),
                "report_path": str(report_path),
                "occupied_voxel_count": report["occupied_voxel_count"],
                "output_brick_count": report["output_brick_count"],
                "reduction_percent": report["reduction_percent"],
                "stability": report["stability"],
            }
        )
    summary = {
        "samples": sample_reports,
        "target_studs": int(target_studs),
        "sculpture_mode": sculpture_mode,
        "wall_thickness": int(wall_thickness),
        "base_thickness": int(base_thickness),
        "voxel_smoothing": voxel_smoothing,
        "infill_density": float(infill_density),
        "optimizer": optimizer,
    }
    summary_path = output_dir / "mesh_sample_comparison.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    summary["summary_path"] = str(summary_path)
    return summary
