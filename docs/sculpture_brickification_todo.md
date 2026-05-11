# Sculpture Brickification TODO

This document tracks the Studio-like sculpture conversion improvements for MakeYourBrick.

Reference behavior from BrickLink Studio Sculpture import:

- converts OBJ/STL into a LEGO sculpture
- builds the sculpture layer by layer
- exposes base size, wall thickness, base thickness, brick selection, color mode, orientation, and layer step options
- can run connection checks after import

MakeYourBrick will keep its mesh-first pipeline and add a sculpture-oriented brickification mode around the existing voxel and LDraw stages.

## Target Flow

```text
mesh or SAM output
  -> repair
  -> voxelization
  -> sculpture occupancy post-process
       solid: keep filled occupancy
       shell: keep surface/walls and fill base layers
  -> layer-aware brickification
  -> stability report
  -> LDR with optional 0 STEP per layer
```

## Phase 1: Layer Step Output

Status: completed.

Purpose:

Make generated LDR files easier to inspect and build by inserting `0 STEP` markers whenever the vertical layer changes.

Tasks:

- [x] Add `step_by_layer` option to `write_ldr()`.
- [x] Insert `0 STEP` between different brick `y` layers.
- [x] Keep the default output unchanged unless requested.
- [x] Add tests for layer step insertion and default behavior.
- [x] Add CLI/API option `--steps-by-layer` / `steps_by_layer`.

Acceptance criteria:

- [x] LDR output can be opened as layer-by-layer instructions.
- [x] Existing LDR tests continue to pass.

## Phase 2: Sculpture Occupancy Mode

Status: completed.

Purpose:

Support Studio-like solid and shell sculpture modes.

Tasks:

- [x] Add `sculpture_mode`: `solid` or `shell`.
- [x] Add `wall_thickness` in studs.
- [x] Add `base_thickness` in layers.
- [x] In `solid` mode, keep the current filled occupancy.
- [x] In `shell` mode, keep surface voxels within `wall_thickness` of empty space or model boundary.
- [x] Always fill the bottom `base_thickness` layers inside the occupied footprint.
- [x] Preserve voxel color IDs for retained voxels.
- [x] Add tests for hollowing, wall thickness, base thickness, and color preservation.

Acceptance criteria:

- [x] Shell mode reduces occupied voxels on a solid fixture.
- [x] Base layers remain solid.
- [x] Shell mode never adds voxels outside the original occupancy.

## Phase 3: Layer-Aware Brick Optimizer

Status: completed.

Purpose:

Improve stability and build quality beyond largest-first greedy placement.

Tasks:

- [x] Keep existing `greedy_brickify()` unchanged.
- [x] Add `layered_brickify()` with scored candidate placement.
- [x] Score candidates with:
  - brick area
  - support ratio from the layer below
  - overhang penalty
  - vertical seam alignment penalty
  - color consistency
- [x] Prefer stable candidates over slightly larger unstable candidates.
- [x] Add tests for support-aware selection and seam staggering.

Acceptance criteria:

- [x] Occupancy is preserved.
- [x] Color boundaries are preserved.
- [x] Support and seam metrics are deterministic and covered by targeted tests.

## Phase 4: Stability Report

Status: completed.

Purpose:

Make sculpture output quality visible and measurable.

Tasks:

- [x] Add `build_stability_report()`.
- [x] Report unsupported brick count.
- [x] Report floating brick count.
- [x] Report average support ratio.
- [x] Report vertical seam alignment score.
- [x] Report layer count.
- [x] Include `sculpture_mode`, `wall_thickness`, and `base_thickness`.
- [x] Merge stability fields into optimizer report JSON.

Acceptance criteria:

- [x] Reports show both brick reduction and stability metrics.
- [x] Metrics are deterministic and covered by tests.

## Phase 5: CLI and Backend Options

Status: completed.

Purpose:

Expose sculpture controls through command-line and local backend flows.

Tasks:

- [x] Add CLI options:
  - `--sculpture-mode solid|shell`
  - `--wall-thickness`
  - `--base-thickness`
  - `--steps-by-layer`
  - `--optimizer greedy|layered`
- [x] Add backend `JobRequest` fields with validation.
- [x] Pass settings through `run_from_image()` and `convert_mesh_to_ldr()`.
- [x] Update usage docs and architecture docs.

Acceptance criteria:

- [x] Existing defaults match current behavior.
- [x] New options work through mesh CLI, image CLI, and backend jobs.
- [x] Full test suite passes.

## Deferred Work

- True Studio connectivity checks.
- Broader brick palette and plate support.
- Cost-aware or inventory-aware brick selection.

## Phase 6: LDraw Placement Calibration

Status: completed.

Purpose:

Match Stud.io/LDraw placement expectations for the basic brick set before deeper optimizer work.

Tasks:

- [x] Calibrate part placement around the LDraw part center origin.
- [x] Keep 1x1 placement unchanged.
- [x] Offset larger brick origins by half their footprint.
- [x] Preserve right-angle rotation matrices.
- [x] Add a placement fixture generator for Stud.io visual inspection.
- [x] Add tests for 2x4, 1x4, 2x2, 1x2, and 1x1 placement.

Acceptance criteria:

- [x] Large bricks cover the same voxel footprint as equivalent 1x1 bricks.
- [x] The fixture can be generated with `scripts/make_ldraw_placement_fixture.py`.
- [x] The fixture includes all currently supported basic brick parts and a rotated 2x4 case.

## Phase 7: Mesh Sample Quality Comparison

Status: completed.

Purpose:

Create repeatable mesh fixtures so sculpture quality can be compared across shape classes before and after optimizer changes.

Tasks:

- [x] Add procedural mesh samples for a sphere, bust-like shape, and object-like shape.
- [x] Convert samples through the same mesh-to-LDR pipeline used by real SAM outputs.
- [x] Write per-sample LDR files and optimizer reports.
- [x] Write one JSON summary with brick counts, reduction ratio, and stability metrics.
- [x] Add tests for sample mesh creation and one end-to-end sample comparison.

Acceptance criteria:

- [x] Sample comparison can be generated with `scripts/compare_mesh_samples.py`.
- [x] Summary reports include artifact paths and stability metrics.
- [x] The comparison uses shell sculpture mode, layered optimizer, and layer-step output by default.

## Phase 8: OBJ Orientation and Studio Part Set Alignment

Status: completed.

Purpose:

Fix Z-up OBJ imports that appeared sideways in LDraw viewers and make optimizer output closer to Studio sculpture imports.

Tasks:

- [x] Add mesh orientation support before voxelization.
- [x] Add `up_axis`: `auto`, `none`, `x`, `y`, or `z`.
- [x] Rotate clearly dominant Z-up meshes into the pipeline Y-up coordinate system by default.
- [x] Record mesh orientation details in the optimizer report JSON.
- [x] Expand the default brick candidate set with Studio-style long bricks:
  - `3006.dat` 2x10
  - `3007.dat` 2x8
  - `2456.dat` 2x6
  - `3008.dat` 1x8
  - `3009.dat` 1x6
  - `3002.dat` 2x3
  - `3622.dat` 1x3
- [x] Add tests for orientation inference and longer brick selection.

Acceptance criteria:

- [x] Z-up OBJ assets no longer lie sideways after conversion.
- [x] Queen OBJ converts to a 60-layer upright LDR when using `--target-studs 60 --up-axis auto`.
- [x] The optimizer can use the same long brick families seen in the Studio import output.

## Phase 9: Studio-Like Ray Voxelizer

Status: completed.

Purpose:

Reduce holes and broken silhouettes on open OBJ/STL sculpture assets where surface voxelization cannot build reliable filled volumes.

Tasks:

- [x] Add `surface` and `ray` voxelizer options.
- [x] Keep `surface` as the compatibility path for existing tests and watertight meshes.
- [x] Add vertical scanline voxelization that casts one ray through each stud column.
- [x] Fill paired ray-intersection intervals along the vertical axis.
- [x] Handle odd ray hit counts by filling between first and last hit for sculpture-style open meshes.
- [x] Add CLI/API pass-through for `--voxelizer surface|ray`.
- [x] Add tests for ray voxelization.

Acceptance criteria:

- [x] `queen.obj` can be converted with `--up-axis auto --voxelizer ray --target-studs 60`.
- [x] The generated model is upright, layer-stepped, and one connected component.

## Phase 10: Studio Reference Diff Diagnostics

Status: completed.

Purpose:

Use user-generated Studio `.io` outputs as black-box reference data, then measure where MakeYourBrick output diverges layer by layer without copying Studio internals.

Tasks:

- [x] Parse Studio `.io` archives and embedded LDraw model files.
- [x] Load rectangular brick footprint metadata from Studio's split/merge catalog when available locally.
- [x] Convert reference and candidate LDR parts into stud footprint cells.
- [x] Compare total shared, missing, and extra footprint occupancy.
- [x] Add X/Z alignment modes:
  - `origin`
  - `best-xz`
  - `none`
- [x] Try axis-aligned X/Z rotations and mirrors in `best-xz` mode to avoid false negatives from coordinate convention differences.
- [x] Add per-layer diff diagnostics:
  - reference voxels
  - candidate voxels
  - shared voxels
  - missing voxels
  - extra voxels
  - layer IoU
  - missing and extra X/Z bounds
- [x] Add worst-layer summaries for missing, extra, and IoU.
- [x] Add tests for layer diagnostics and best X/Z alignment.

Acceptance criteria:

- [x] `scripts/compare_studio_ldr.py` writes a JSON report with layer-by-layer differences.
- [x] The queen comparison runs against `queen.io` and `outputs/ldr/queen_ray_solid_60.ldr`.
- [x] Diagnostics show the current output still diverges strongly from Studio, especially around lower/middle layers.

Latest queen diagnostic:

- Alignment selected by `best-xz`: `mirror_x`, offset `[23, 2, -35]`.
- IoU: `0.125026`.
- Missing footprint cells: `4954`.
- Extra footprint cells: `7846`.
- Worst missing layers: 4, 3, 5, 2, 6.
- Worst extra layers: 5, 9, 10, 8, 7.

## Phase 11: Studio-Guided Voxel Tuning

Status: in progress.

Purpose:

Use the Phase 10 diagnostics to improve mesh-to-voxel behavior before further brick optimizer changes.

Tasks:

- [x] Add layer profile reports for reference vs candidate width/depth/area curves.
- [x] Detect candidate under-scale or axis compression from layer bounds.
- [x] Add optional voxel smoothing presets for sculpture imports.
- [ ] Improve ray voxelizer column filling near thin silhouettes.
- [ ] Add contour cleanup to remove isolated protrusions per layer.
- [ ] Re-run queen comparison after each tuning change and track IoU, missing, and extra deltas.

Acceptance criteria:

- [ ] Queen output has fewer visible holes and fewer isolated protrusions.
- [ ] Studio comparison IoU improves over the Phase 10 baseline.
- [ ] Layer-level extra/missing spikes are reduced in the lower and middle layers.

Latest light smoothing diagnostic:

- Baseline IoU: `0.125026`, missing `4954`, extra `7846`.
- `voxel_smoothing=light` IoU: `0.125188`, missing `4952`, extra `7843`.
- Interpretation: light smoothing removes a few unsupported protrusions without changing scale. The main quality gap is still voxel fill/profile shape, not isolated spur cleanup alone.
