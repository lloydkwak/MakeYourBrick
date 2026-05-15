# MakeYourBrick

MakeYourBrick converts a 2D image or an OBJ/STL mesh into a Studio-like LDraw `.ldr` LEGO sculpture.

The repository now keeps one focused production path:

```text
image or mesh
  -> triangle mesh (.obj preferred)
  -> Y-up orientation
  -> base-size layer slicing
  -> contour shell + filled bottom layers
  -> Studio brick-combination tiling
  -> layer-colored LDraw output
```

## Current Scope

Implemented and kept:

- OBJ/STL mesh loading through Trimesh
- optional SAM 3D command runner that must export a triangle mesh
- Studio-like base-size scaling
- layer-slice voxelization
- wall thickness and bottom thickness
- Studio sculpture brick set: `1x2`, `1x3`, `1x4`, `1x6`, `1x8`, `2x2`, `2x3`, `2x4`, `2x6`, `2x8`
- layer color sequence observed from Studio output: `15, 3, 2, 19, 20, 27, 13, 1`
- LDraw `0 STEP` output by layer
- JSON conversion report
- minimal FastAPI + local web shell for image upload, placeholder selection, and conversion jobs

Removed from the active code path:

- synthetic voxel demos
- legacy greedy/plate/experimental BrickFormer-style solvers
- mesh sample comparison utilities
- Studio `.io` analysis scripts
- old broad test suite for removed experiments

## Install

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Mesh To LDraw

```bash
python scripts/mesh_to_ldr.py \
  --mesh queen.obj \
  --base-size-studs 32 \
  --wall-thickness 2 \
  --base-thickness 3 \
  --report outputs/reports/queen_report.json \
  --output outputs/ldr/queen.ldr
```

## Image To LDraw

`image_to_ldr.py` expects a SAM command that writes a Trimesh-loadable mesh to `{output}`.

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --mask data/masks/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "python your_sam_export.py --image {image} --mask {mask} --output {output}" \
  --base-size-studs 32 \
  --wall-thickness 2 \
  --base-thickness 3 \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

## Local API

```bash
python -m uvicorn makeyourbrick.server.main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

Open `apps/web/index.html` and set API base URL to `http://127.0.0.1:8000`.

## Verify

```bash
python -m compileall src scripts tests
python -m pytest
```

## Docs

- [Architecture](docs/architecture.md)
- [Usage](docs/usage.md)
- [Environment](docs/environment.md)
- [Testing](docs/testing.md)
- [References](docs/references.md)
