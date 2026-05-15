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
- vertical support generation for overhangs
- Studio brick-combination tiling
- layer color sequence
- mesh-to-LDR CLI smoke conversion
- all-1x1 target debug output
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
