# Usage

Run commands from the repository root.

## Install

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

For lightweight local mesh tests, `torch` and SAM 3D are not required. For real SAM 3D inference, see `docs/sam3d_manual_setup.md`.

## Synthetic Voxel to LDraw

Generate a 1x1-brick synthetic box:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 3 2 --color 16 --output outputs/ldr/synthetic_box.ldr
```

Generate an optimized synthetic model:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 1 2 --color 16 --optimize --output outputs/ldr/optimized_box.ldr
```

## Mesh to LDraw

Convert a mesh with default LDraw color:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 24 --output outputs/ldr/mesh_output.ldr
```

Convert a mesh with a constant RGB color quantized to LDraw:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 24 --rgb 242 205 55 --output outputs/ldr/yellow_mesh_output.ldr
```

Convert a colored mesh using nearest vertex/face color sampling:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample_colored.ply --target-studs 8 --sample-colors --output outputs/ldr/sampled_color_mesh.ldr
```

Convert with greedy brick optimization and write a report:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample_colored.ply --target-studs 8 --sample-colors --optimize --report outputs/reports/mesh_report.json --output outputs/ldr/sampled_color_mesh.ldr
```

Convert with an explicit mesh repair mode and repair report:

```bash
python scripts/mesh_to_ldr.py \
  --mesh data/examples/sample.stl \
  --repair-mode basic \
  --repair-report outputs/reports/repair_report.json \
  --target-studs 24 \
  --output outputs/ldr/mesh_output.ldr
```

Supported repair modes:

- `none`: preserve loaded mesh geometry apart from export processing
- `basic`: Trimesh cleanup, duplicate/degenerate face removal, hole filling, and normal fixing
- `manifold`: use `manifold3d` when available; falls back to `basic` with a report warning if unavailable or unsuccessful
- `convex-hull`: replace the model with a watertight convex outer approximation

## Mesh Inspection

Inspect a mesh before conversion:

```bash
python scripts/inspect_mesh.py --mesh outputs/meshes/raw_model.glb --report outputs/reports/mesh_inspect.json
```

The report records asset type, geometry count, vertices, faces, bounds, watertightness, color availability, warnings, and whether the artifact is ready for voxelization.

## Image to LDraw

The image pipeline requires a SAM-compatible command template that writes a triangle mesh to `{output}`.

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "<command that writes {output}>" \
  --target-studs 48 \
  --sample-colors \
  --optimize \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

Supported command placeholders:

- `{image}`
- `{output}`
- `{output_dir}`
- `{repo}`

## SAM 3D Adapter

Adapt an existing SAM output candidate into a MakeYourBrick mesh:

```bash
python scripts/adapters/sam3d_to_mesh.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --candidate path/to/sam/output.glb \
  --output outputs/meshes/raw_model.glb \
  --report outputs/reports/sam3d_adapter.json
```

Or wrap an upstream SAM command:

```bash
python scripts/adapters/sam3d_to_mesh.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --output outputs/meshes/raw_model.glb \
  --sam-command "<command that writes {output} or files under {work_dir}>"
```

The adapter validates that the selected artifact is a triangle mesh before handing it to voxelization. See `docs/sam3d_adapter.md`.

## Outputs

Generated files are ignored by Git:

- `outputs/meshes/`
- `outputs/voxels/`
- `outputs/ldr/`
- `outputs/reports/`

## Local Backend

Run the FastAPI backend:

```bash
python -m uvicorn makeyourbrick.server.main:app --app-dir src --reload
```

Backend endpoints:

- `GET /api/health`
- `POST /api/images`
- `GET /api/images/{image_id}/file`
- `POST /api/images/{image_id}/selection`
- `GET /api/masks/{mask_id}/file?image_id={image_id}`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/result`
- `GET /api/jobs/{job_id}/files/{kind}`

The current job endpoint is a local stub. It uses a deterministic fake SAM mesh and then runs the real MakeYourBrick conversion pipeline, producing LDR, voxel, mesh, mesh inspection, mesh repair, and optimizer report artifacts under `outputs/ui_sessions/<image_id>/jobs/<job_id>/`.

Start a browser workflow by opening:

```text
apps/web/index.html
```

Then upload an image, select a target object, and press `Run Conversion`.
