from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

REQUIRED_CHECKPOINT_FILES = (
    "pipeline.yaml",
    "ss_encoder.safetensors",
    "ss_generator.ckpt",
    "ss_decoder.ckpt",
    "slat_generator.ckpt",
    "slat_decoder_mesh.ckpt",
    "slat_decoder_gs.ckpt",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export a SAM 3D Objects reconstruction as a GLB mesh.")
    parser.add_argument("--image", required=True, help="Input RGB/RGBA image path.")
    parser.add_argument("--mask", required=True, help="Input object mask PNG path.")
    parser.add_argument("--output", required=True, help="Output mesh path, usually raw_model.glb.")
    parser.add_argument("--repo", default="/opt/sam-3d-objects", help="SAM 3D Objects repo path.")
    parser.add_argument("--tag", default="hf", help="Checkpoint tag under checkpoints/<tag>.")
    parser.add_argument(
        "--checkpoint-model-id",
        default=os.environ.get("MAKEYOURBRICK_SAM3D_MODEL_ID", "facebook/sam-3d-objects"),
        help="Hugging Face model id used when checkpoints/<tag> is missing.",
    )
    parser.add_argument(
        "--checkpoint-dir",
        type=Path,
        default=None,
        help="Use this existing checkpoint directory instead of repo/checkpoints/<tag>.",
    )
    parser.add_argument(
        "--local-files-only",
        action="store_true",
        help="Resolve SAM 3D checkpoints from the local Hugging Face cache only.",
    )
    parser.add_argument("--seed", type=int, default=42, help="SAM 3D random seed.")
    parser.add_argument(
        "--depth-device",
        default="cpu",
        choices=("cpu", "cuda", "staged-cuda"),
        help=(
            "Device for the MoGe depth model. cpu is safest on 10-12 GB GPUs. "
            "cuda keeps MoGe resident with SAM 3D and can OOM. staged-cuda runs "
            "MoGe on GPU first, frees it, then loads SAM 3D with a supplied pointmap."
        ),
    )
    parser.add_argument(
        "--dino-dtype",
        default="fp16",
        choices=("fp32", "fp16"),
        help="DINO condition embedder precision. fp16 is an experimental low-memory mode.",
    )
    parser.add_argument(
        "--image-size",
        type=int,
        default=448,
        help=(
            "SAM 3D conditioning image size. 518 is the checkpoint default; "
            "448 uses less VRAM and is better for 10 GB GPUs."
        ),
    )
    parser.add_argument(
        "--pointmap-size",
        type=int,
        default=256,
        help="PointPatchEmbed input size. Keep 256 unless using a checkpoint patched for another size.",
    )
    parser.add_argument(
        "--pointmap-condition",
        default="disabled",
        choices=("enabled", "disabled"),
        help=(
            "Whether to run PointPatchEmbed inside the SAM 3D condition embedder. "
            "disabled saves VRAM on 10 GB GPUs while still using pointmaps for pose/scale preprocessing."
        ),
    )
    parser.add_argument(
        "--free-before-decode",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Move no-longer-needed SAM 3D modules to CPU before mesh decoding to reduce peak VRAM.",
    )
    parser.add_argument("--compile", action="store_true", help="Enable torch.compile for repeated inference.")
    parser.add_argument(
        "--mesh-postprocess",
        action="store_true",
        help="Enable SAM mesh postprocessing. Slower, but may improve mesh quality.",
    )
    parser.add_argument(
        "--texture-baking",
        action="store_true",
        help="Enable SAM texture baking. Much slower and needs more GPU memory.",
    )
    return parser.parse_args()


def _checkpoint_config_path(directory: Path) -> Path:
    return directory / "pipeline.yaml"


def _checkpoint_dir_ready(directory: Path) -> bool:
    return all((directory / name).exists() for name in REQUIRED_CHECKPOINT_FILES)


def _cached_checkpoint_dir(model_id: str) -> Path | None:
    cache_text = (
        os.environ.get("HF_HUB_CACHE")
        or os.environ.get("HUGGINGFACE_HUB_CACHE")
        or str(Path(os.environ.get("HF_HOME", Path.home() / ".cache" / "huggingface")) / "hub")
    )
    repo_cache_name = f"models--{model_id.replace('/', '--')}"
    snapshot_root = Path(cache_text).expanduser() / repo_cache_name / "snapshots"
    if not snapshot_root.exists():
        return None
    checkpoint_dirs = sorted(
        (path.parent for path in snapshot_root.glob("*/checkpoints/pipeline.yaml")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for checkpoint_dir in checkpoint_dirs:
        if _checkpoint_dir_ready(checkpoint_dir):
            return checkpoint_dir
    return None


def _link_checkpoint_dir(source: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        if target.resolve() == source.resolve():
            return True
        if target.is_symlink() or target.is_file():
            target.unlink()
        elif target.is_dir() and not any(target.iterdir()):
            target.rmdir()
        else:
            return False
    target.symlink_to(source.resolve(), target_is_directory=True)
    return True


def resolve_checkpoint_dir(args: argparse.Namespace, repo: Path) -> Path:
    if args.checkpoint_dir is not None:
        checkpoint_dir = args.checkpoint_dir.expanduser().resolve()
        if not _checkpoint_dir_ready(checkpoint_dir):
            raise FileNotFoundError(f"SAM 3D checkpoint directory is incomplete: {checkpoint_dir}")
        return checkpoint_dir

    checkpoint_dir = repo / "checkpoints" / args.tag
    if _checkpoint_dir_ready(checkpoint_dir):
        return checkpoint_dir

    cached_dir = _cached_checkpoint_dir(args.checkpoint_model_id)
    if cached_dir is not None:
        if _link_checkpoint_dir(cached_dir, checkpoint_dir):
            return checkpoint_dir
        return cached_dir

    try:
        from huggingface_hub import snapshot_download
    except ImportError as exc:
        raise RuntimeError(
            "huggingface_hub is required to auto-download SAM 3D checkpoints. "
            "Install huggingface-hub or mount an existing checkpoint directory."
        ) from exc

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if token is None and not args.local_files_only:
        token = True

    snapshot_path = Path(
        snapshot_download(
            repo_id=args.checkpoint_model_id,
            repo_type="model",
            allow_patterns=["checkpoints/*"],
            local_files_only=args.local_files_only,
            token=token,
        )
    )
    downloaded_dir = snapshot_path / "checkpoints"
    if not _checkpoint_dir_ready(downloaded_dir):
        raise FileNotFoundError(
            f"SAM 3D checkpoint directory is incomplete after downloading {args.checkpoint_model_id}: "
            f"{downloaded_dir}"
        )

    try:
        if _link_checkpoint_dir(downloaded_dir, checkpoint_dir):
            return checkpoint_dir
    except OSError:
        pass
    fallback_dir = repo / "checkpoints" / f"{args.tag}-snapshot"
    if _checkpoint_dir_ready(fallback_dir):
        return fallback_dir
    shutil.copytree(downloaded_dir, fallback_dir, dirs_exist_ok=True)
    return fallback_dir


def merge_image_and_mask(image, mask):
    import numpy as np
    from PIL import Image

    image_array = np.array(image)
    mask_array = np.array(normalize_mask_for_alpha(mask))
    if mask_array.ndim == 2:
        mask_array = mask_array[..., None]
    merged = np.concatenate([image_array[..., :3], mask_array], axis=-1)
    return Image.fromarray(merged.astype(np.uint8))


def normalize_mask_for_alpha(mask):
    import numpy as np
    from PIL import Image

    mask_array = np.array(mask)
    if mask_array.size and mask_array.max() <= 1:
        mask_array = mask_array.astype(np.uint8) * 255
    else:
        mask_array = mask_array.astype(np.uint8)
    return Image.fromarray(mask_array)


def set_conditioning_sizes(config, image_size: int, pointmap_size: int) -> None:
    from omegaconf import DictConfig, ListConfig

    if isinstance(config, DictConfig):
        for key in list(config.keys()):
            value = config[key]
            if key in {"size", "input_size"} and value == 518:
                config[key] = image_size
            elif key == "input_size" and value == 256:
                config[key] = pointmap_size
            else:
                set_conditioning_sizes(value, image_size, pointmap_size)
    elif isinstance(config, ListConfig):
        for value in config:
            set_conditioning_sizes(value, image_size, pointmap_size)


def write_resized_subconfig(config_path: Path, output_dir: Path, image_size: int, pointmap_size: int):
    from omegaconf import OmegaConf

    subconfig = OmegaConf.load(config_path)
    set_conditioning_sizes(subconfig, image_size, pointmap_size)
    output_dir.mkdir(parents=True, exist_ok=True)
    resized_path = output_dir / config_path.name
    OmegaConf.save(subconfig, resized_path)
    return resized_path


def apply_conditioning_sizes(
    config,
    config_path: Path,
    output_path: Path,
    image_size: int,
    pointmap_size: int,
) -> None:
    if image_size == 518 and pointmap_size == 256:
        return

    set_conditioning_sizes(config, image_size, pointmap_size)
    resized_dir = output_path.parent / "_sam3d_lowmem_configs"
    for key in ("ss_generator_config_path", "slat_generator_config_path"):
        original = config_path.parent / config[key]
        config[key] = str(write_resized_subconfig(original, resized_dir, image_size, pointmap_size))


def patch_condition_embedder_fp16() -> None:
    import torch
    from sam3d_objects.pipeline import inference_pipeline as pipeline_module

    original_init = pipeline_module.InferencePipeline.init_ss_condition_embedder
    original_embed = pipeline_module.InferencePipeline.embed_condition

    def init_ss_condition_embedder_fp16(self, *init_args, **init_kwargs):
        embedder = original_init(self, *init_args, **init_kwargs)
        if embedder is not None:
            embedder.half()
        return embedder

    def embed_condition_fp16(self, condition_embedder, *embed_args, **embed_kwargs):
        if condition_embedder is None:
            return original_embed(self, condition_embedder, *embed_args, **embed_kwargs)
        with torch.autocast(device_type="cuda", dtype=torch.float16):
            return original_embed(self, condition_embedder, *embed_args, **embed_kwargs)

    pipeline_module.InferencePipeline.init_ss_condition_embedder = init_ss_condition_embedder_fp16
    pipeline_module.InferencePipeline.embed_condition = embed_condition_fp16


def patch_pointmap_condition_disabled() -> None:
    import torch
    from sam3d_objects.model.backbone.dit.embedder import pointmap as pointmap_module

    def pointmap_zero_forward(self, xyz: torch.Tensor, valid_mask=None) -> torch.Tensor:
        batch_size = xyz.shape[0]
        windows_per_side = self.input_size // self.patch_size
        token_count = windows_per_side * windows_per_side
        dtype = self.pos_embed.dtype
        return torch.zeros(
            batch_size,
            token_count,
            self.embed_dim,
            device=xyz.device,
            dtype=dtype,
        )

    pointmap_module.PointPatchEmbed.forward = pointmap_zero_forward


def patch_free_before_decode() -> None:
    import gc
    import torch
    from sam3d_objects.pipeline import inference_pipeline as pipeline_module

    original_decode_slat = pipeline_module.InferencePipeline.decode_slat

    def decode_slat_lowmem(self, slat, formats):
        keep_on_gpu = {"slat_decoder_mesh"}
        for name, model in list(self.models.items()):
            if name in keep_on_gpu or model is None:
                continue
            model.to("cpu")
        for embedder in getattr(self, "condition_embedders", {}).values():
            if embedder is not None:
                embedder.to("cpu")
        gc.collect()
        torch.cuda.empty_cache()
        return original_decode_slat(self, slat, formats)

    pipeline_module.InferencePipeline.decode_slat = decode_slat_lowmem


def patch_mesh_only_postprocess() -> None:
    from sam3d_objects.model.backbone.tdfy_dit.utils import postprocessing_utils
    from sam3d_objects.pipeline import inference_pipeline as pipeline_module

    original_postprocess = pipeline_module.InferencePipeline.postprocess_slat_output

    def postprocess_slat_output_mesh_only(
        self,
        outputs,
        with_mesh_postprocess,
        with_texture_baking,
        use_vertex_color,
    ):
        if "mesh" in outputs and "gaussian" not in outputs:
            outputs["glb"] = postprocessing_utils.to_glb(
                None,
                outputs["mesh"][0],
                simplify=0.95,
                texture_size=1024,
                verbose=False,
                with_mesh_postprocess=with_mesh_postprocess,
                with_texture_baking=False,
                use_vertex_color=True,
                rendering_engine=self.rendering_engine,
            )
            return outputs
        return original_postprocess(
            self,
            outputs,
            with_mesh_postprocess,
            with_texture_baking,
            use_vertex_color,
        )

    pipeline_module.InferencePipeline.postprocess_slat_output = postprocess_slat_output_mesh_only


def precompute_pointmap_on_gpu(config, image, mask):
    import gc
    import numpy as np
    import torch
    from hydra.utils import instantiate
    from pytorch3d.transforms import Transform3d
    from sam3d_objects.pipeline.inference_pipeline_pointmap import camera_to_pytorch3d_camera

    depth_config = config.depth_model.copy()
    depth_config.device = "cuda"
    depth_model = instantiate(depth_config)
    merged_image = merge_image_and_mask(image, mask)
    image_float = (np.array(merged_image).astype(np.float32) / 255.0)
    rgb_tensor = torch.from_numpy(image_float).permute(2, 0, 1).contiguous()[:3]
    with torch.no_grad(), torch.autocast(device_type="cuda", dtype=torch.float16):
        output = depth_model(rgb_tensor)
        pointmaps = output["pointmaps"]
        camera_transform = (
            Transform3d()
            .rotate(camera_to_pytorch3d_camera(device="cuda").rotation)
            .to("cuda")
        )
        pointmap = camera_transform.transform_points(pointmaps.float()).detach().cpu().float()

    del depth_model, output, pointmaps, camera_transform
    torch.cuda.empty_cache()
    gc.collect()
    return pointmap


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).resolve()
    image_path = Path(args.image).resolve()
    mask_path = Path(args.mask).resolve()
    output_path = Path(args.output).resolve()

    if not repo.exists():
        raise FileNotFoundError(f"SAM 3D repo not found: {repo}")
    checkpoint_dir = resolve_checkpoint_dir(args, repo)
    config_path = _checkpoint_config_path(checkpoint_dir)
    if not image_path.exists():
        raise FileNotFoundError(f"Input image not found: {image_path}")
    if not mask_path.exists():
        raise FileNotFoundError(f"Input mask not found: {mask_path}")

    if "CONDA_PREFIX" not in os.environ:
        os.environ["CONDA_PREFIX"] = str(Path(sys.executable).resolve().parents[1])

    sys.path.insert(0, str(repo / "notebook"))
    from hydra.utils import instantiate
    from omegaconf import OmegaConf
    from inference import BLACKLIST_FILTERS, WHITELIST_FILTERS, check_hydra_safety, load_image, load_mask  # type: ignore

    if args.dino_dtype == "fp16":
        import torch
        from sam3d_objects.model.backbone.dit.embedder import dino as dino_module

        dino_init = dino_module.Dino.__init__

        def low_memory_dino_init(self, *init_args, **init_kwargs):
            with torch.device("cpu"):
                dino_init(self, *init_args, **init_kwargs)
            self.half()

        dino_module.Dino.__init__ = low_memory_dino_init
        patch_condition_embedder_fp16()
    if args.pointmap_condition == "disabled":
        patch_pointmap_condition_disabled()
    if args.free_before_decode:
        patch_free_before_decode()
    patch_mesh_only_postprocess()

    image = load_image(str(image_path))
    mask = normalize_mask_for_alpha(load_mask(str(mask_path)))

    config = OmegaConf.load(config_path)
    config.rendering_engine = "pytorch3d"
    config.compile_model = args.compile
    config.workspace_dir = str(config_path.parent)
    apply_conditioning_sizes(config, config_path, output_path, args.image_size, args.pointmap_size)
    config.slat_decoder_gs_config_path = None
    config.slat_decoder_gs_4_config_path = None
    pointmap = None
    if args.depth_device == "staged-cuda":
        pointmap = precompute_pointmap_on_gpu(config, image, mask)
        config.depth_model = {
            "_target_": "sam3d_objects.pipeline.depth_models.moge.MoGe",
            "model": {"_target_": "torch.nn.Identity"},
            "device": "cpu",
        }
    else:
        config.depth_model.device = args.depth_device
    check_hydra_safety(config, WHITELIST_FILTERS, BLACKLIST_FILTERS)
    pipeline = instantiate(config)

    if args.depth_device == "cpu":
        import torch

        depth_infer = pipeline.depth_model.model.infer

        def depth_infer_to_pipeline_device(*infer_args, **infer_kwargs):
            output = depth_infer(*infer_args, **infer_kwargs)
            return {
                key: value.to(device=pipeline.device, dtype=torch.float32)
                if isinstance(value, torch.Tensor)
                else value
                for key, value in output.items()
            }

        pipeline.depth_model.model.infer = depth_infer_to_pipeline_device

    output = pipeline.run(
        image,
        mask,
        seed=args.seed,
        with_mesh_postprocess=args.mesh_postprocess,
        with_texture_baking=args.texture_baking,
        with_layout_postprocess=False,
        use_vertex_color=not args.texture_baking,
        pointmap=pointmap,
        decode_formats=["mesh"],
    )

    mesh = output.get("glb")
    if mesh is None:
        raise RuntimeError(f"SAM 3D output did not include a GLB mesh. Output keys: {sorted(output)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(output_path)
    print(f"Saved SAM 3D mesh to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
