# Testing

## Full Verification

```bash
python -m compileall src scripts tests/fake_sam3d_command.py
python -m pytest
```

The current suite covers:

- synthetic voxel generation
- 1x1 brickification
- greedy brick optimization
- LDraw coordinate and rotation output
- color palette loading and CIELAB quantization
- mesh loading and cleanup
- mesh color sampling
- voxel artifact save/load
- mesh-to-LDraw CLI
- image-to-LDraw orchestration with a fake SAM command
- optimizer report generation

## Test Design

The test suite does not require a GPU or SAM 3D Objects installation. Image pipeline tests use `tests/fake_sam3d_command.py`, which emits a small colored mesh artifact.

## Manual Smoke Tests

Synthetic optimized output:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 1 2 --color 16 --optimize --output outputs/ldr/optimized_box.ldr
```

Mesh optimized output:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 8 --optimize --output outputs/ldr/mesh_optimized.ldr
```

Fake image pipeline:

```bash
python scripts/image_to_ldr.py \
  --image outputs/manual_fake_image.png \
  --sam-repo . \
  --sam-command "python tests/fake_sam3d_command.py --output {output} --colored-box" \
  --target-studs 8 \
  --sample-colors \
  --optimize \
  --report outputs/reports/manual_image_report.json \
  --output outputs/ldr/manual_image_output.ldr
```

Create the fake image first if needed:

```bash
python -c "from pathlib import Path; Path('outputs/manual_fake_image.png').parent.mkdir(parents=True, exist_ok=True); Path('outputs/manual_fake_image.png').write_bytes(b'fake-image')"
```

