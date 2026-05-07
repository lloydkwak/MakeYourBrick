# SAM 3D Mesh Export TODO

This document tracks the revised integration plan for `facebookresearch/sam-3d-objects`.

The primary path is no longer Gaussian-splat-to-mesh conversion. The preferred path is to use the upstream model's mesh/GLB output directly, then pass that triangle mesh into the existing MakeYourBrick mesh-first pipeline.

References:

- Repository: https://github.com/facebookresearch/sam-3d-objects
- Inference pipeline: `sam3d_objects/pipeline/inference_pipeline.py`
- Post-processing utility: `sam3d_objects/model/backbone/tdfy_dit/utils/postprocessing_utils.py`

## Target Contract

```text
image.png
mask.png
  -> SAM 3D Objects adapter
  -> raw_model.glb
  -> mesh inspection
  -> mesh repair
  -> voxelization
  -> brickification
  -> output.ldr
```

The adapter should treat GLB or triangle mesh export as the successful path. Gaussian splat PLY should remain a debug artifact.

## Output Priority

1. `output["glb"].export(raw_model.glb)`
2. `output["mesh"][0]` converted through `trimesh.Trimesh(vertices, faces)` and exported to GLB
3. Preserve `output["gs"].save_ply(raw_splat.ply)` as debug output
4. Fail clearly if only Gaussian splat PLY or point cloud data is available

## Phase A: Mask-Aware Runner Contract

Purpose:

Allow every image-to-mesh runner to receive the selected object mask from the UI/backend.

Tasks:

- Add optional `mask_path` to `Sam3DRunner.generate()`.
- Add `{mask}` command template placeholder.
- Add optional `mask_path` to `run_from_image()`.
- Pass backend job `mask_id` artifact into `run_from_image()`.
- Keep fake runner compatible for local UI tests.
- Add tests for mask placeholder rendering and backend job mask forwarding.

Acceptance criteria:

- Existing fake UI jobs still complete.
- Command runner can receive `--mask {mask}`.
- Missing mask paths fail before running an external command.
- Full test suite passes.

## Phase B: Adapter CLI Mask Support

Status: completed.

Purpose:

Prepare `scripts/adapters/sam3d_to_mesh.py` for the real SAM object mask.

Tasks:

- [x] Add `--mask` argument.
- [x] Add `{mask}` placeholder to adapter command rendering.
- [x] Include `mask_path` in adapter reports.
- [x] Validate that `--mask` exists when provided.
- [x] Add tests for command template mask forwarding.

Acceptance criteria:

- Adapter command can be called as:

```bash
python scripts/adapters/sam3d_to_mesh.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --mask outputs/ui_sessions/<image_id>/masks/<mask_id>.png \
  --output outputs/meshes/raw_model.glb \
  --report outputs/reports/sam3d_adapter.json
```

## Phase C: Real SAM Mesh Export Script

Purpose:

Create the concrete script that imports SAM 3D Objects and exports a MakeYourBrick-ready GLB.

Planned file:

```text
scripts/adapters/run_sam3d_objects_export.py
```

Tasks:

- Load image and mask.
- Run the official SAM 3D Objects inference path.
- Prefer `output["glb"].export(output_path)`.
- Fallback to `output["mesh"][0]` to GLB via Trimesh.
- Optionally save `output["gs"]` as `raw_splat.ply`.
- Write an adapter metadata JSON.
- Fail with explicit messages when mesh/GLB output is unavailable.

Acceptance criteria:

- Script has a documented CLI.
- Script can be used as `MAKEYOURBRICK_SAM_COMMAND`.
- The resulting GLB passes `scripts/inspect_mesh.py`.

## Phase D: Backend Real SAM Mode

Purpose:

Run the real adapter through the existing backend job system.

Tasks:

- Set `MAKEYOURBRICK_RUNNER_MODE=sam3d`.
- Set `MAKEYOURBRICK_SAM_REPO`.
- Set `MAKEYOURBRICK_SAM_COMMAND` to the adapter command.
- Run UI upload, selection, conversion, and artifact download.
- Verify job status and failure messages.

Acceptance criteria:

- UI job produces `.ldr`, reports, raw mesh, cleaned mesh, and voxels from a real image.
- Errors are readable when SAM fails.

## Phase E: Manual Quality Gate

Purpose:

Confirm that the first complete pipeline result is usable outside Python tests.

Tasks:

- Open `raw_model.glb` in Blender or Windows 3D Viewer.
- Open `output.ldr` in Stud.io or an LDraw-compatible viewer.
- Check scale, orientation, brick placement, color sampling, and part origins.
- Record findings in `docs/roadmap.md`.

Acceptance criteria:

- One real image-to-LDraw sample is documented.
- Remaining issues are categorized as quality improvements, not pipeline blockers.
