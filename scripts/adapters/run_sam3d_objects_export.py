from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SAM 3D Objects and export a MakeYourBrick-ready GLB mesh.")
    parser.add_argument("--repo", type=Path, required=True, help="SAM 3D Objects repository path.")
    parser.add_argument("--image", type=Path, required=True, help="Input RGB/RGBA image path.")
    parser.add_argument("--mask", type=Path, required=True, help="Object mask image path.")
    parser.add_argument("--output", type=Path, required=True, help="Output triangle mesh path, usually .glb.")
    parser.add_argument(
        "--config",
        type=Path,
        help="SAM 3D pipeline config path. Defaults to <repo>/checkpoints/hf/pipeline.yaml.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Inference seed.")
    parser.add_argument("--compile", action="store_true", help="Enable upstream model compilation.")
    parser.add_argument("--splat-output", type=Path, help="Optional debug Gaussian splat PLY output path.")
    parser.add_argument("--metadata", type=Path, help="Optional metadata JSON output path.")
    return parser.parse_args()


def to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value)


def load_image(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        image.load()
        return np.asarray(image.convert("RGB"), dtype=np.uint8)


def load_mask(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        image.load()
        mask = np.asarray(image.convert("L"), dtype=np.uint8)
    return mask > 0


def load_inference_class(repo_path: Path):
    notebook_path = repo_path / "notebook"
    if not notebook_path.exists():
        raise FileNotFoundError(f"SAM 3D notebook directory not found: {notebook_path}")
    sys.path.insert(0, str(notebook_path))
    try:
        from inference import Inference  # type: ignore
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError(
            "Could not import SAM 3D Objects notebook inference API. "
            f"Install the upstream environment and check repo path: {repo_path}"
        ) from error
    return Inference


def first_mesh_entry(mesh_output: Any) -> Any:
    if isinstance(mesh_output, (list, tuple)):
        if not mesh_output:
            raise ValueError("SAM output['mesh'] is empty.")
        return mesh_output[0]
    return mesh_output


def tensor_mesh_to_trimesh(mesh: Any):
    try:
        import trimesh
    except ModuleNotFoundError as error:
        raise ModuleNotFoundError("trimesh is required for mesh fallback export.") from error

    if hasattr(mesh, "vertices") and hasattr(mesh, "faces"):
        vertices = to_numpy(mesh.vertices)
        faces = to_numpy(mesh.faces)
    elif hasattr(mesh, "verts_packed") and hasattr(mesh, "faces_packed"):
        vertices = to_numpy(mesh.verts_packed())
        faces = to_numpy(mesh.faces_packed())
    else:
        raise ValueError("SAM mesh output does not expose vertices/faces or PyTorch3D packed mesh accessors.")

    if vertices.size == 0 or faces.size == 0:
        raise ValueError("SAM mesh output contains no vertices or faces.")

    tri_mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    vertex_colors = getattr(mesh, "vertex_colors", None)
    if vertex_colors is not None:
        colors = to_numpy(vertex_colors)
        if len(colors) == len(tri_mesh.vertices):
            tri_mesh.visual.vertex_colors = colors
    return tri_mesh


def maybe_save_splat(output: dict[str, Any], splat_output_path: Path | None) -> str | None:
    if splat_output_path is None:
        return None
    splat = output.get("gs") or output.get("gaussian")
    if isinstance(splat, (list, tuple)):
        splat = splat[0] if splat else None
    if splat is None or not hasattr(splat, "save_ply"):
        return None
    splat_output_path.parent.mkdir(parents=True, exist_ok=True)
    splat.save_ply(str(splat_output_path))
    return str(splat_output_path)


def export_sam3d_output(
    output: dict[str, Any],
    output_path: Path,
    *,
    splat_output_path: Path | None = None,
) -> dict[str, Any]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    splat_path = maybe_save_splat(output, splat_output_path)

    glb = output.get("glb")
    if glb is not None and hasattr(glb, "export"):
        glb.export(output_path)
        return {
            "status": "completed",
            "export_method": "output_glb",
            "output_path": str(output_path),
            "splat_output_path": splat_path,
            "output_keys": sorted(output.keys()),
        }

    if "mesh" in output:
        mesh = tensor_mesh_to_trimesh(first_mesh_entry(output["mesh"]))
        mesh.export(output_path)
        return {
            "status": "completed",
            "export_method": "mesh_to_trimesh_glb",
            "output_path": str(output_path),
            "splat_output_path": splat_path,
            "output_keys": sorted(output.keys()),
        }

    raise ValueError(
        "SAM 3D output did not contain exportable GLB or triangle mesh data. "
        f"Available keys: {sorted(output.keys())}. "
        "If only Gaussian splats are available, mesh extraction is required before MakeYourBrick voxelization."
    )


def write_metadata(metadata: dict[str, Any], path: Path | None) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_export(
    *,
    repo_path: Path,
    image_path: Path,
    mask_path: Path,
    output_path: Path,
    config_path: Path | None = None,
    seed: int = 42,
    compile_model: bool = False,
    splat_output_path: Path | None = None,
    metadata_path: Path | None = None,
) -> dict[str, Any]:
    if not repo_path.exists():
        raise FileNotFoundError(f"SAM 3D Objects repo not found: {repo_path}")
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")
    if not mask_path.exists():
        raise FileNotFoundError(f"Input mask not found: {mask_path}")

    config_path = config_path or repo_path / "checkpoints" / "hf" / "pipeline.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"SAM 3D config not found: {config_path}")

    inference_cls = load_inference_class(repo_path)
    inference = inference_cls(str(config_path), compile=compile_model)
    output = inference(load_image(image_path), load_mask(mask_path), seed=seed)
    metadata = export_sam3d_output(output, output_path, splat_output_path=splat_output_path)
    metadata.update(
        {
            "repo_path": str(repo_path),
            "image_path": str(image_path),
            "mask_path": str(mask_path),
            "config_path": str(config_path),
            "seed": seed,
        }
    )
    write_metadata(metadata, metadata_path)
    return metadata


def main() -> None:
    args = parse_args()
    metadata = run_export(
        repo_path=args.repo,
        image_path=args.image,
        mask_path=args.mask,
        output_path=args.output,
        config_path=args.config,
        seed=args.seed,
        compile_model=args.compile,
        splat_output_path=args.splat_output,
        metadata_path=args.metadata,
    )
    print(
        "Exported SAM 3D mesh: "
        f"method={metadata['export_method']} output={metadata['output_path']}"
    )


if __name__ == "__main__":
    main()
