# SAM 3D Objects Manual Setup

This document records the real SAM 3D Objects setup path for manual end-to-end verification.

Sources checked on 2026-05-06:

- https://github.com/facebookresearch/sam-3d-objects
- https://github.com/facebookresearch/sam-3d-objects/blob/main/doc/setup.md

## Hardware and OS Notes

The upstream setup guide currently targets:

- Linux 64-bit
- NVIDIA GPU
- at least 32 GB VRAM

This is heavier than the local MakeYourBrick mesh pipeline. Keep SAM 3D installed under `third_party/sam-3d-objects` and do not commit it.

## External Repo Layout

```bash
git clone https://github.com/facebookresearch/sam-3d-objects third_party/sam-3d-objects
```

## Environment Setup

Follow the upstream `doc/setup.md` inside the external repo. At a high level, it uses:

```bash
mamba env create -f environments/default.yml
mamba activate sam3d-objects
pip install -e '.[dev]'
pip install -e '.[p3d]'
pip install -e '.[inference]'
```

The upstream guide also requires CUDA/PyTorch package indexes and a small patching step. Check the official setup page before running this on a GPU machine.

## Checkpoints

SAM 3D Objects checkpoints are distributed through Hugging Face and may require access approval and authentication.

The upstream guide uses the `facebook/sam-3d-objects` model repo and downloads checkpoints under the external repo's `checkpoints/` directory.

## MakeYourBrick Command Contract

`scripts/image_to_ldr.py` does not assume a fixed SAM 3D CLI because the upstream repo is notebook/demo oriented and may change. Instead, it accepts:

```bash
--sam-command "<command template>"
```

The command template can use these placeholders:

- `{image}`: input image path
- `{mask}`: selected object mask path
- `{output}`: expected output mesh path
- `{output_dir}`: output mesh directory
- `{repo}`: SAM 3D repo path

The command must create the file at `{output}` in a mesh format supported by Trimesh. OBJ is preferred.

The prepared MakeYourBrick wrapper is:

```bash
python scripts/adapters/run_sam3d_objects_export.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --mask data/masks/sample.png \
  --output outputs/meshes/raw_model.obj \
  --splat-output outputs/meshes/raw_splat.ply \
  --metadata outputs/reports/sam3d_export.json
```

## Manual Verification Shape

After the external SAM environment is installed and a sample mask exists, run:

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --mask data/masks/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "python scripts/adapters/run_sam3d_objects_export.py --repo {repo} --image {image} --mask {mask} --output {output} --metadata {output_dir}/sam3d_export.json" \
  --raw-mesh outputs/meshes/raw_model.obj \
  --target-studs 48 \
  --sample-colors \
  --optimize \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

## Important Caveat

The upstream quick-start demo demonstrates saving a Gaussian splat PLY. MakeYourBrick's downstream pipeline expects a Trimesh-loadable triangle mesh. The local wrapper prefers `output["mesh"][0]` exported as OBJ, can still export GLB when requested, and saves splat PLY only as an optional debug artifact.
