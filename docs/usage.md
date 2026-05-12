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

Convert with Studio-like sculpture options:

```bash
python scripts/mesh_to_ldr.py \
  --mesh data/examples/sample.stl \
  --target-studs 48 \
  --target-width-studs 38 \
  --target-depth-studs 37 \
  --up-axis auto \
  --voxelizer slice \
  --ray-fill wide \
  --optimize \
  --optimizer layered \
  --brick-palette studio \
  --sculpture-mode density \
  --wall-thickness 1 \
  --base-thickness 2 \
  --infill-density 0.35 \
  --infill-pattern ribs \
  --voxel-smoothing studio \
  --steps-by-layer \
  --report outputs/reports/sculpture_report.json \
  --output outputs/ldr/sculpture_output.ldr
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

Mesh orientation:

- `--up-axis auto`: detect a clearly dominant source axis and rotate it to pipeline Y-up
- `--up-axis z`: use this for known Z-up OBJ/STL sculpture assets
- `--up-axis y`: keep Y-up assets upright
- `--up-axis none`: disable orientation changes

Voxelization:

- `--voxelizer surface`: use Trimesh surface voxelization and fill; best for watertight meshes
- `--voxelizer ray`: cast vertical rays through each stud column; better for Studio-like sculpture imports from open OBJ/STL assets
- `--voxelizer slice`: slice the mesh layer by layer, project section contours to X/Z, and fill each layer; closest to Studio's sculpture import model. The slice path unions same-layer contours to avoid false holes from open OBJ contour fragments.
- `--ray-fill wide|balanced`: choose how odd ray-hit columns are filled; `wide` preserves the original broad fill behavior, while `balanced` drops one outlier hit to reduce overfilled columns
- `--target-width-studs` / `--target-depth-studs`: optional Studio-style base footprint scaling before voxelization

## Mesh Inspection

Inspect a mesh before conversion:

```bash
python scripts/inspect_mesh.py --mesh outputs/meshes/raw_model.glb --report outputs/reports/mesh_inspect.json
```

The report records asset type, geometry count, vertices, faces, bounds, watertightness, color availability, warnings, and whether the artifact is ready for voxelization.

## Image to LDraw

The image pipeline requires a SAM-compatible command template that writes a triangle mesh to `{output}`. If an object mask is available, pass it with `--mask` and use the `{mask}` command placeholder.

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --mask outputs/ui_sessions/<image_id>/masks/<mask_id>.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "<command that reads {image} and {mask}, then writes {output}>" \
  --target-studs 48 \
  --sample-colors \
  --optimize \
  --optimizer layered \
  --sculpture-mode shell \
  --wall-thickness 1 \
  --base-thickness 2 \
  --steps-by-layer \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

Supported command placeholders:

- `{image}`
- `{mask}`
- `{output}`
- `{output_dir}`
- `{repo}`

Sculpture options:

- `--sculpture-mode solid|shell|contour-shell|density`: keep a fully solid model, keep a 3D surface shell, keep per-layer contour walls, or keep shell/base plus deterministic lattice infill
- `--wall-thickness`: number of voxel/stud layers to keep from the surface in shell mode
- `--base-thickness`: number of bottom layers to force solid
- `--infill-density`: target interior lattice density for `density` sculpture mode
- `--infill-pattern lattice|ribs`: choose uniform lattice infill or staggered Studio-like internal support ribs
- `--voxel-smoothing none|light|contour|studio|profile|polished`: optional cleanup for isolated protrusions, layer contours, Studio-like layer consistency, stricter profile cleanup, or polished contour cleanup that further reduces jagged surface noise
- `--optimizer greedy|layered`: largest-first greedy optimizer or support/seam-aware optimizer
- `--brick-palette full|studio|compact|plates`: choose the full experimental set, the Studio-reference sculpture set, a compact visual-debug set, or a plate-only set
- `--height-unit brick|plate`: choose full-brick vertical layers or plate-height vertical layers. `plate` requires `--optimize --brick-palette plates` because a plate is one third of a brick height.
- `--steps-by-layer`: insert `0 STEP` markers between vertical layers in the LDR file

## Placement and Quality Fixtures

Generate an LDraw placement fixture for Stud.io visual inspection:

```bash
python scripts/make_ldraw_placement_fixture.py --steps-by-layer
```

Generate repeatable mesh quality samples and reports:

```bash
python scripts/compare_mesh_samples.py --target-studs 8
```

The comparison script creates sphere, bust-like, and object-like meshes, converts them with shell sculpture mode and the layered optimizer, and writes a JSON summary under `outputs/quality/mesh_samples`.

Compare a Studio `.io` reference against a MakeYourBrick LDR output:

```bash
python scripts/compare_studio_ldr.py \
  --reference queen.io \
  --candidate outputs/ldr/queen_ray_solid_60.ldr \
  --studio-dir "Studio 2.0" \
  --alignment best-xz \
  --output outputs/reports/queen_studio_vs_ray_comparison.json
```

The Studio comparison script uses `.io`/LDraw output as black-box reference data. It reports total footprint IoU, missing/extra cells, selected X/Z alignment, and layer-by-layer missing/extra diagnostics.

## SAM 3D Adapter

Adapt an existing SAM output candidate into a MakeYourBrick mesh:

```bash
python scripts/adapters/sam3d_to_mesh.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --mask outputs/ui_sessions/<image_id>/masks/<mask_id>.png \
  --candidate path/to/sam/output.glb \
  --output outputs/meshes/raw_model.glb \
  --report outputs/reports/sam3d_adapter.json
```

Or wrap an upstream SAM command:

```bash
python scripts/adapters/sam3d_to_mesh.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --mask outputs/ui_sessions/<image_id>/masks/<mask_id>.png \
  --output outputs/meshes/raw_model.glb \
  --sam-command "<command that reads {image} and {mask}, then writes {output} or files under {work_dir}>"
```

Run the prepared SAM 3D Objects GLB export wrapper directly:

```bash
python scripts/adapters/run_sam3d_objects_export.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --mask outputs/ui_sessions/<image_id>/masks/<mask_id>.png \
  --output outputs/meshes/raw_model.glb \
  --splat-output outputs/meshes/raw_splat.ply \
  --metadata outputs/reports/sam3d_export.json
```

The adapter validates that the selected artifact is a triangle mesh before handing it to voxelization. See `docs/sam3d_adapter.md`.

SAM 3D Objects commonly saves Gaussian splat PLY files. Those files are raw visualization/debug artifacts, not the default LEGO conversion input. If the adapter detects a Gaussian splat PLY or point cloud PLY, it writes a clear failure report and stops before voxelization.

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
- `GET /api/config`
- `POST /api/images`
- `GET /api/images/{image_id}/file`
- `POST /api/images/{image_id}/selection`
- `GET /api/masks/{mask_id}/file?image_id={image_id}`
- `POST /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/result`
- `GET /api/jobs/{job_id}/files/{kind}`

The job endpoint defaults to a deterministic fake SAM mesh and then runs the real MakeYourBrick conversion pipeline, producing LDR, voxel, mesh, mesh inspection, mesh repair, and optimizer report artifacts under `outputs/ui_sessions/<image_id>/jobs/<job_id>/`.

Backend runner configuration:

- `MAKEYOURBRICK_RUNNER_MODE=fake`: default local integration runner
- `MAKEYOURBRICK_RUNNER_MODE=command`: run a command template through `Sam3DRunner`
- `MAKEYOURBRICK_RUNNER_MODE=sam3d`: alias for command mode when wiring the real SAM adapter
- `MAKEYOURBRICK_SAM_REPO=third_party/sam-3d-objects`: external repository path
- `MAKEYOURBRICK_SAM_COMMAND="<command that reads {image} and {mask}, then writes {output}>"`
- SAM command placeholders include `{image}`, `{mask}`, `{output}`, `{output_dir}`, and `{repo}`
- `MAKEYOURBRICK_SAM_TIMEOUT_SECONDS=3600`

Example real SAM 3D backend configuration:

```powershell
$env:MAKEYOURBRICK_RUNNER_MODE = "sam3d"
$env:MAKEYOURBRICK_SAM_REPO = "third_party/sam-3d-objects"
$env:MAKEYOURBRICK_SAM_COMMAND = "python scripts/adapters/run_sam3d_objects_export.py --repo {repo} --image {image} --mask {mask} --output {output} --metadata {output_dir}/sam3d_export.json"
$env:MAKEYOURBRICK_SAM_TIMEOUT_SECONDS = "3600"
python -m uvicorn makeyourbrick.server.main:app --app-dir src --reload
```

In `sam3d` mode, `POST /api/jobs` requires a `mask_id`. The UI flow should upload an image, submit a selection, then start the conversion job with the returned mask id.

Backend job requests also accept:

- `optimizer`: `greedy` or `layered`
- `brick_palette`: `full`, `studio`, `compact`, or `plates`
- `height_unit`: `brick` or `plate`
- `sculpture_mode`: `solid`, `shell`, or `density`
- `wall_thickness`
- `base_thickness`
- `infill_density`
- `infill_pattern`: `lattice` or `ribs`
- `voxel_smoothing`: `none`, `light`, `contour`, `studio`, `profile`, or `polished`
- `ray_fill`: `wide` or `balanced`
- `steps_by_layer`

Start a browser workflow by opening:

```text
apps/web/index.html
```

Then upload an image, select a target object, and press `Run Conversion`.
