# Phase 4.5 TODO: Mesh Color Sampling and Optimizer Reports

This temporary working document tracks Phase 4.5 until it is fully implemented and verified.

## Goal

Improve the local mesh pipeline before SAM 3D integration by adding:

- mesh-derived voxel RGB sampling
- optimizer summary reports

The target flow is:

```text
mesh -> voxel centers -> nearest mesh color -> LDraw color IDs -> optimized bricks -> report + .ldr
```

## Mesh Color Sampling

Phase 4.5 adds a pragmatic first sampling implementation:

1. Voxelize the mesh.
2. Convert occupied voxel indices to world-space voxel centers.
3. If mesh vertex colors are available, sample the nearest vertex color using `scipy.spatial.cKDTree`.
4. If face colors are available, sample nearest triangle-center face color.
5. If no mesh color data exists, fall back to the configured default RGB.
6. Quantize sampled RGB values through the existing LDraw palette path.

This is not full texture UV sampling yet. It is intentionally a robust midpoint between constant color and full material/texture support.

## Optimizer Report

The report is JSON and records:

- occupancy shape
- occupied voxel count
- unoptimized brick count
- output brick count
- brick reduction count and percent
- part counts
- color counts
- optimization mode

## Completion Checklist

- [x] Add Phase 4.5 TODO document.
- [x] Add mesh color sampling helpers and tests.
- [x] Connect sampled mesh colors to voxel artifacts.
- [x] Add optimizer report generation helpers and tests.
- [x] Add CLI options for sampled colors and report path.
- [ ] Add end-to-end tests for sampled color and report output.
- [ ] Run verification commands.
- [ ] Commit and push each completed feature checkpoint.

## Verification Commands

```bash
python -m compileall src scripts
python -m pytest
python scripts/mesh_to_ldr.py --mesh data/examples/sample_colored.ply --target-studs 8 --sample-colors --optimize --report outputs/reports/mesh_report.json --output outputs/ldr/sampled_color_mesh.ldr
```

## Done Definition

- All tests pass.
- Vertex-colored meshes can produce quantized LDraw color IDs without `--rgb`.
- The optimizer report is written as valid JSON.
- Existing `--rgb`, `--color`, and `--optimize` behavior remains compatible.
