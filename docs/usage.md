# Usage

## Mesh Conversion

```bash
python scripts/mesh_to_ldr.py \
  --mesh queen.obj \
  --base-size-studs 32 \
  --wall-thickness 2 \
  --base-thickness 3 \
  --report outputs/reports/queen_report.json \
  --output outputs/ldr/queen.ldr
```

Options:

- `--mesh`: input OBJ/STL or any Trimesh-loadable triangle mesh
- `--base-size-studs`: maximum horizontal footprint in studs, or `auto` to choose from 16/24/32/48/64 using mesh proportions and complexity
- `--wall-thickness`: shell wall width in studs
- `--base-thickness`: number of bottom layers to fill completely
- `--up-axis`: `auto`, `none`, `x`, `y`, or `z`
- `--voxels`: optional `.npz` voxel artifact path
- `--debug-target-output`: optional all-1x1 LDraw target preview for separating voxelization issues from brick placement issues
- `--report`: JSON report path
- `--output`: LDraw output path

## Image Conversion

`image_to_ldr.py` runs an external SAM command first. The command must create a triangle mesh at `{output}`.

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

Supported command placeholders:

- `{image}`
- `{mask}`
- `{output}`
- `{output_dir}`
- `{repo}`

## Local Web Shell

Start the backend:

```bash
python -m uvicorn makeyourbrick.server.main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
apps/web/index.html
```

The backend defaults to a fake local mesh runner unless configured with:

```text
MAKEYOURBRICK_RUNNER_MODE=command
MAKEYOURBRICK_SAM_REPO=third_party/sam-3d-objects
MAKEYOURBRICK_SAM_COMMAND=<command template>
```

Use `MAKEYOURBRICK_RUNNER_MODE=sam3d` when the command requires a user mask.

## Output

The converter writes:

- `.ldr`: LDraw model with per-layer `0 STEP`
- `.npz`: voxel occupancy artifact
- `.json`: conversion report

The report includes:

- voxel shape
- target voxel count
- output brick count
- part counts
- color counts
- orientation report
- footprint/base-size report
- stability summary
- lower/upper attachment counts
- selected voxelizer (`slice` or `surface`)
- selected sculpture mode (`contour-shell` for closed slice output or `surface-detail` for fragmented open OBJ output)

For vehicle-style OBJ files made from many open sub-meshes, start with:

```bash
python scripts/mesh_to_ldr.py \
  --mesh car.obj \
  --base-size-studs auto \
  --wall-thickness 2 \
  --base-thickness 3 \
  --up-axis y \
  --report outputs/reports/car_report.json \
  --output outputs/ldr/car.ldr
```
