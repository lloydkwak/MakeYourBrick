# SAM 3D Objects Manual Setup

This document records the real SAM 3D Objects setup path for Phase 5 manual verification.

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
- `{output}`: expected output mesh path
- `{output_dir}`: output mesh directory
- `{repo}`: SAM 3D repo path

The command must create the file at `{output}` in a mesh format supported by Trimesh, such as `.ply`, `.glb`, `.obj`, or `.stl`.

## Manual Verification Shape

Once a real SAM adapter command exists, run:

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "<your SAM adapter command using {image} and {output}>" \
  --raw-mesh outputs/meshes/raw_model.ply \
  --target-studs 48 \
  --sample-colors \
  --optimize \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

## Important Caveat

The upstream quick-start demo currently demonstrates saving a Gaussian splat PLY. MakeYourBrick's downstream pipeline expects a Trimesh-loadable surface mesh. If the SAM output is a point cloud or Gaussian splat rather than a triangle mesh, an adapter/conversion step is required before voxelization.

