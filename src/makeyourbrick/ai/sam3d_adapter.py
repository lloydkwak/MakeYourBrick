from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

try:
    import trimesh
except ModuleNotFoundError:  # pragma: no cover - exercised only when optional deps are absent.
    trimesh = None

from makeyourbrick.mesh.inspect import inspect_mesh


MESH_SUFFIXES = {".glb", ".gltf", ".obj", ".ply", ".stl"}
GAUSSIAN_PLY_PROPERTIES = {
    "opacity",
    "scale_0",
    "scale_1",
    "scale_2",
    "rot_0",
    "rot_1",
    "rot_2",
    "rot_3",
    "f_dc_0",
    "f_dc_1",
    "f_dc_2",
}


def read_ply_header(path: Path) -> dict:
    header_lines: list[str] = []
    with path.open("rb") as file:
        for raw_line in file:
            line = raw_line.decode("ascii", errors="ignore").strip()
            header_lines.append(line)
            if line == "end_header":
                break
            if len(header_lines) > 2048:
                raise ValueError(f"PLY header is too large or missing end_header: {path}")
    if not header_lines or header_lines[0] != "ply":
        raise ValueError(f"Not a PLY file: {path}")

    elements: dict[str, int] = {}
    properties: dict[str, list[str]] = {}
    current_element: str | None = None
    for line in header_lines:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "element" and len(parts) >= 3:
            current_element = parts[1]
            elements[current_element] = int(parts[2])
            properties.setdefault(current_element, [])
        elif parts[0] == "property" and current_element and len(parts) >= 2:
            properties[current_element].append(parts[-1])
    return {"elements": elements, "properties": properties, "header_lines": header_lines}


def classify_sam_artifact(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".ply":
        header = read_ply_header(path)
        elements = header["elements"]
        vertex_properties = set(header["properties"].get("vertex", []))
        has_faces = elements.get("face", 0) > 0
        gaussian_markers = sorted(vertex_properties.intersection(GAUSSIAN_PLY_PROPERTIES))
        if has_faces:
            artifact_type = "mesh_ply"
            mesh_compatible = True
            next_action = "adapt_to_glb"
        elif gaussian_markers:
            artifact_type = "gaussian_splat_ply"
            mesh_compatible = False
            next_action = "mesh_extraction_required"
        else:
            artifact_type = "point_cloud_ply"
            mesh_compatible = False
            next_action = "mesh_reconstruction_required"
        return {
            "artifact_type": artifact_type,
            "mesh_compatible": mesh_compatible,
            "next_action": next_action,
            "elements": elements,
            "vertex_properties": sorted(vertex_properties),
            "gaussian_markers": gaussian_markers,
        }
    return {
        "artifact_type": "mesh_candidate",
        "mesh_compatible": suffix in MESH_SUFFIXES,
        "next_action": "inspect_and_adapt",
        "elements": {},
        "vertex_properties": [],
        "gaussian_markers": [],
    }


def render_command(
    command_template: str,
    *,
    repo_path: Path,
    image_path: Path,
    mask_path: Path | None = None,
    output_path: Path,
    work_dir: Path,
) -> list[str]:
    rendered = command_template.format(
        repo=str(repo_path),
        image=str(image_path),
        mask=str(mask_path) if mask_path is not None else "",
        output=str(output_path),
        output_dir=str(output_path.parent),
        work_dir=str(work_dir),
    )
    return shlex.split(rendered, posix=(os.name != "nt"))


def run_sam_command(
    command_template: str,
    *,
    repo_path: Path,
    image_path: Path,
    mask_path: Path | None = None,
    output_path: Path,
    work_dir: Path,
    timeout_seconds: int,
) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)
    command = render_command(
        command_template,
        repo_path=repo_path,
        image_path=image_path,
        mask_path=mask_path,
        output_path=output_path,
        work_dir=work_dir,
    )
    result = subprocess.run(
        command,
        cwd=repo_path,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "SAM adapter command failed with exit code "
            f"{result.returncode}.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )


def find_mesh_candidate(search_dirs: list[Path], output_path: Path) -> Path:
    candidates: list[Path] = []
    for directory in search_dirs:
        if not directory.exists():
            continue
        candidates.extend(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in MESH_SUFFIXES and path != output_path
        )
    if output_path.exists():
        return output_path
    if not candidates:
        raise FileNotFoundError(
            "No SAM mesh artifact found. Expected one of: " + ", ".join(sorted(MESH_SUFFIXES))
        )
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _load_exportable_mesh(candidate_path: Path):
    if trimesh is None:
        raise ModuleNotFoundError("trimesh is required for SAM mesh adaptation.")
    loaded = trimesh.load(candidate_path)
    if isinstance(loaded, trimesh.Trimesh):
        return loaded
    if isinstance(loaded, trimesh.Scene):
        meshes = [geometry for geometry in loaded.geometry.values() if isinstance(geometry, trimesh.Trimesh)]
        if not meshes:
            raise ValueError("SAM output scene does not contain triangle mesh geometry.")
        return trimesh.util.concatenate(meshes)
    raise ValueError(f"SAM output is not a triangle mesh: {type(loaded).__name__}")


def adapt_sam_output(
    *,
    repo_path: Path,
    image_path: Path,
    mask_path: Path | None = None,
    output_path: Path,
    command_template: str | None = None,
    candidate_path: Path | None = None,
    work_dir: Path | None = None,
    report_path: Path | None = None,
    timeout_seconds: int = 3600,
) -> dict:
    if not repo_path.exists():
        raise FileNotFoundError(f"SAM 3D Objects repo not found: {repo_path}")
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")
    if mask_path is not None and not mask_path.exists():
        raise FileNotFoundError(f"Input mask not found: {mask_path}")

    work_dir = work_dir or output_path.parent / "sam3d_adapter_workspace"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if command_template:
        run_sam_command(
            command_template,
            repo_path=repo_path,
            image_path=image_path,
            mask_path=mask_path,
            output_path=output_path,
            work_dir=work_dir,
            timeout_seconds=timeout_seconds,
        )

    candidate = candidate_path or find_mesh_candidate([work_dir, output_path.parent], output_path)
    artifact_report = classify_sam_artifact(candidate)
    source_report = inspect_mesh(candidate)
    if not artifact_report["mesh_compatible"]:
        adapter_report = {
            "repo_path": str(repo_path),
            "image_path": str(image_path),
            "mask_path": str(mask_path) if mask_path is not None else None,
            "candidate_path": str(candidate),
            "output_path": str(output_path),
            "source_artifact": artifact_report,
            "source_inspection": source_report,
            "output_inspection": None,
            "status": "failed",
            "failure_reason": artifact_report["next_action"],
        }
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(adapter_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise ValueError(
            "SAM output is not a triangle mesh artifact. "
            f"Detected {artifact_report['artifact_type']}; {artifact_report['next_action']}."
        )
    if not source_report["voxelization_ready"]:
        raise ValueError(
            "SAM output is not a voxelization-ready triangle mesh. "
            f"Candidate: {candidate}. Errors: {source_report['errors']}"
        )

    if candidate != output_path:
        mesh = _load_exportable_mesh(candidate)
        mesh.export(output_path)

    output_report = inspect_mesh(output_path)
    adapter_report = {
        "repo_path": str(repo_path),
        "image_path": str(image_path),
        "mask_path": str(mask_path) if mask_path is not None else None,
        "candidate_path": str(candidate),
        "output_path": str(output_path),
        "source_artifact": artifact_report,
        "source_inspection": source_report,
        "output_inspection": output_report,
        "status": "completed" if output_report["voxelization_ready"] else "failed",
    }
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(adapter_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not output_report["voxelization_ready"]:
        raise ValueError(f"Adapted output is not voxelization-ready: {output_report['errors']}")
    return adapter_report
