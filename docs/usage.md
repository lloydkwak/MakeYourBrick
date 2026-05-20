# Usage

## Web App

The recommended path is the Docker SAM runtime:

```bash
docker run --rm --gpus all -p 8000:8000 \
  -e HF_TOKEN \
  -v "$(pwd)/outputs:/workspace/MakeYourBrick/outputs" \
  -v "$(pwd)/third_party/sam-3d-objects/torch-cache:/root/.cache/torch" \
  -v "$(pwd)/third_party/sam-3d-objects/hf-cache:/root/.cache/huggingface" \
  -e 'MAKEYOURBRICK_SAM_COMMAND=python /workspace/MakeYourBrick/scripts/sam3d_export.py --repo {repo} --depth-device staged-cuda --dino-dtype fp16 --image {image} --mask {mask} --output {output}' \
  makeyourbrick-sam3d:local
```

Open:

```text
http://127.0.0.1:8000
```

Flow:

- upload or drag in an image
- click points or draw a box on the object
- wait for the SAM2 mask overlay
- press `Generate model`
- inspect the raw SAM 3D GLB preview
- download the `.ldr`

## Mesh Conversion

```bash
python scripts/mesh_to_ldr.py \
  --mesh queen.glb \
  --base-size-studs auto \
  --wall-thickness 2 \
  --base-thickness 3 \
  --up-axis auto \
  --color-strategy mesh \
  --report outputs/reports/queen_report.json \
  --output outputs/ldr/queen.ldr
```

Options:

- `--mesh`: input OBJ/GLB/STL or any Trimesh-loadable triangle mesh
- `--base-size-studs`: maximum horizontal footprint in studs, or `auto` to choose from `16/24/32/48`
- `--wall-thickness`: shell wall width in studs
- `--base-thickness`: number of bottom layers to fill completely
- `--up-axis`: `auto`, `none`, `x`, `y`, or `z`
- `--color-strategy`: `mesh` for mesh-sampled colors, or `layer` for Studio-like debug layer colors
- `--voxels`: optional `.npz` voxel artifact path
- `--debug-target-output`: optional all-1x1 LDraw target preview
- `--report`: JSON report path
- `--output`: LDraw output path

## Image CLI

`image_to_ldr.py` runs an external SAM command first. The command must create a
triangle mesh at `{output}`.

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --mask data/masks/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "python scripts/sam3d_export.py --repo {repo} --image {image} --mask {mask} --output {output}" \
  --base-size-studs auto \
  --wall-thickness 2 \
  --base-thickness 3 \
  --color-strategy mesh \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

Supported command placeholders:

- `{image}`
- `{mask}`
- `{output}`
- `{output_dir}`
- `{repo}`

## Output

Each completed job can write:

- `raw_model.glb`: raw SAM 3D or input mesh artifact
- `output.ldr`: final LDraw model
- `model_voxels.npz`: voxel occupancy and color artifact
- `report.json`: conversion report
- `raw_mesh_inspect.json`: raw mesh inspection report when requested

The report includes:

- selected base size and pitch
- voxelizer (`slice` or `surface`)
- sculpture mode (`contour-shell` or `surface-detail`)
- part counts and color counts
- orientation report
- stability summary
- attachment-only plate overlay counts

## Notes

Mesh color matching samples vertex colors, face colors, UV texture pixels, or
material diffuse colors. Dark photo shadows are softened before LDraw palette
matching, which prevents background lighting from becoming large black/dark
brown LEGO patches.

For fragmented vehicle-style OBJ files, start with:

```bash
python scripts/mesh_to_ldr.py \
  --mesh car.obj \
  --base-size-studs auto \
  --wall-thickness 2 \
  --base-thickness 3 \
  --up-axis y \
  --color-strategy mesh \
  --report outputs/reports/car_report.json \
  --output outputs/ldr/car.ldr
```
