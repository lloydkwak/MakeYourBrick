# Testing

The test suite is intentionally small. It covers only the current core pipeline.

## Run

```bash
python -m compileall src scripts tests
python -m pytest
```

## Covered

- contour-shell target creation
- contour-shell helper mask creation
- bottom layer filling
- Studio brick-combination tiling
- lower/upper attachment-aware stability reporting
- attachment-only plate overlay reporting
- layer color sequence
- CIELAB LDraw colour quantization
- mesh colour strategy brick placement
- mesh-to-LDR CLI smoke conversion
- all-1x1 target debug output
- open mesh surface voxel fallback
- open mesh surface-detail target preservation
- automatic base-size selection
- conversion report output

## Manual Studio Check

For visual inspection:

```bash
python scripts/mesh_to_ldr.py \
  --mesh queen.obj \
  --base-size-studs 32 \
  --wall-thickness 2 \
  --base-thickness 3 \
  --report outputs/reports/queen_report.json \
  --output outputs/ldr/queen.ldr
```

Open `outputs/ldr/queen.ldr` in BrickLink Studio or another LDraw viewer.

For fragmented vehicle-style OBJ files, use Y-up and auto base size:

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

The report should show `sculpture.mode` as `surface-detail` when the open mesh
surface fallback is selected.
