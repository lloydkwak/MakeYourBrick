# Testing

The test suite focuses on the current image/mesh-to-LDraw pipeline.

## Run Locally

```bash
python -m compileall src scripts tests
python -m pytest
```

If the host Python environment does not include the project dependencies, run
tests in the Docker image:

```bash
docker run --rm -v "$(pwd):/workspace/MakeYourBrick" \
  -w /workspace/MakeYourBrick \
  makeyourbrick-sam3d:local \
  python -m pytest
```

## Covered

- contour-shell and surface-detail target creation
- bottom layer filling
- Studio brick-combination tiling
- lower/upper attachment-aware stability reporting
- attachment-only plate overlay reporting
- LDraw writer axes and layer steps
- CIELAB LDraw color quantization
- texture shadow softening
- mesh color strategy and color-boundary preservation
- GLB scene transform preservation
- mesh inspection and color source reporting
- mesh-to-LDR CLI smoke conversion
- all-1x1 target debug output
- open mesh surface voxel fallback
- auto base-size selection, including dense tall meshes resolving to `32`
- fake image runner GLB path
- job runner raw mesh suffix handling

## Manual Checks

Generate a mesh-only LDR:

```bash
python scripts/mesh_to_ldr.py \
  --mesh queen.glb \
  --base-size-studs auto \
  --wall-thickness 2 \
  --base-thickness 3 \
  --color-strategy mesh \
  --report outputs/reports/queen_report.json \
  --output outputs/ldr/queen.ldr
```

Open `outputs/ldr/queen.ldr` in BrickLink Studio or another LDraw viewer.

For the full SAM path, run the Docker UI, generate a model, then inspect:

- the mask overlay in the UI
- the raw GLB preview in the right panel
- the downloaded LDR in Studio
- `outputs/ui_sessions/.../reports/report.json`

The report should show:

- `footprint_scale.base_size_studs`
- `sculpture.color_strategy`
- `color_counts`
- `stability`
- `attachment_overlay`
