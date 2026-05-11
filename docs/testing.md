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
- layered brick optimization
- sculpture shell occupancy mode
- LDraw layer step output
- LDraw placement fixture generation
- stability report metrics
- connected component and overhang-risk metrics
- LDraw coordinate and rotation output
- color palette loading and CIELAB quantization
- mesh loading and cleanup
- mesh inspection reports and CLI
- mesh repair modes and reports
- mesh orientation inference and Y-up conversion
- surface and ray voxelization
- mesh color sampling
- voxel artifact save/load
- mesh-to-LDraw CLI
- image-to-LDraw orchestration with a fake SAM command
- SAM 3D adapter command contract
- SAM 3D Objects GLB export wrapper behavior
- FastAPI image upload and selection endpoints
- FastAPI pipeline job endpoints
- backend `sam3d` mode mask validation
- placeholder segmentation mask generation
- optimizer report generation
- procedural mesh quality sample comparison

## Test Design

The test suite does not require a GPU or SAM 3D Objects installation. Image pipeline tests use `tests/fake_sam3d_command.py`, which emits a small colored mesh artifact.

Backend job tests use `FakeSamMeshRunner` by default and command-mode fake SAM calls for runner integration. Both create deterministic local triangle meshes and then exercise the real mesh cleanup, voxelization, brick optimization, LDraw writer, and report writer.

## Manual Smoke Tests

Synthetic optimized output:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 1 2 --color 16 --optimize --output outputs/ldr/optimized_box.ldr
```

Mesh optimized output:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 8 --optimize --output outputs/ldr/mesh_optimized.ldr
```

Placement fixture for Stud.io:

```bash
python scripts/make_ldraw_placement_fixture.py --steps-by-layer
```

Mesh quality sample comparison:

```bash
python scripts/compare_mesh_samples.py --target-studs 8
```

Fake image pipeline:

```bash
python scripts/image_to_ldr.py \
  --image outputs/manual_fake_image.png \
  --mask outputs/manual_fake_mask.png \
  --sam-repo . \
  --sam-command "python tests/fake_sam3d_command.py --output {output} --mask {mask} --colored-box" \
  --target-studs 8 \
  --sample-colors \
  --optimize \
  --report outputs/reports/manual_image_report.json \
  --output outputs/ldr/manual_image_output.ldr
```

Create the fake image and mask first if needed:

```bash
python -c "from pathlib import Path; Path('outputs/manual_fake_image.png').parent.mkdir(parents=True, exist_ok=True); Path('outputs/manual_fake_image.png').write_bytes(b'fake-image'); Path('outputs/manual_fake_mask.png').write_bytes(b'fake-mask')"
```

Local UI/backend smoke test:

```bash
python -m uvicorn makeyourbrick.server.main:app --app-dir src --reload
```

Open `apps/web/index.html`, set API base URL to `http://127.0.0.1:8000`, upload an image, make a point or box selection, and press `Run Conversion`. The result panel should show LDR, report, and raw mesh links.
