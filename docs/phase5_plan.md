# Phase 5 Plan: SAM 3D Objects Integration

## Goal

Connect the current local mesh-to-LDraw pipeline to SAM 3D Objects so a single image can produce a LEGO `.ldr` output.

The target flow is:

```text
image -> SAM 3D Objects raw mesh -> MakeYourBrick mesh pipeline -> sampled/quantized colors -> optimized LDraw + report
```

## Why This Is Next

Phases 1-4.5 already prove that the project can handle:

- synthetic voxel to LDraw
- mesh to voxel
- RGB/LDraw color quantization
- greedy brick optimization
- sampled mesh colors
- optimizer reports

The remaining major gap is generating the first mesh from a user image.

## Implementation Plan

1. Prepare external dependency layout.
   - Clone `facebookresearch/sam-3d-objects` into `third_party/sam-3d-objects`.
   - Keep the external repo ignored by Git.
   - Document CUDA/GPU requirements separately from the lightweight local pipeline.

2. Harden `Sam3DRunner`.
   - Add config fields for repo path, checkpoint/cache path, output directory, and timeout.
   - Implement subprocess-based execution first because SAM 3D repository APIs may change.
   - Normalize SAM output into `outputs/meshes/raw_model.glb`.

3. Add CLI entry point.
   - Extend `scripts/run_pipeline.py` or add `scripts/image_to_ldr.py`.
   - Support:
     ```bash
     python scripts/image_to_ldr.py --image data/input_images/sample.png --target-studs 48 --sample-colors --optimize --report outputs/reports/image_report.json --output outputs/ldr/image_output.ldr
     ```
   - Preserve `--mesh --skip-ai` fallback.

4. Add integration tests with a fake SAM runner.
   - Do not require GPU in CI/local tests.
   - Use dependency injection or a test stub that emits a known colored mesh.
   - Verify image pipeline orchestration without running the heavy model.

5. Add real manual verification path.
   - Provide a documented command for a GPU machine.
   - Verify generated `raw_model.glb` can be opened independently.
   - Then pass it through the existing mesh pipeline.

## Risks

- SAM 3D install may require specific CUDA/PyTorch versions.
- Model output naming may change.
- Generated meshes may be open, noisy, or non-watertight.
- Texture/material colors may not survive export consistently.

## First Milestone

Implement a robust fake-runner-tested image pipeline wrapper before attempting real GPU inference. This keeps MakeYourBrick testable on machines without SAM 3D installed.

