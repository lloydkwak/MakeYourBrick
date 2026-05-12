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
- Broader brick palette and plate support after a real Studio reference uses those parts.
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

Status: completed.

Purpose:

Use the Phase 10 diagnostics to improve mesh-to-voxel behavior before further brick optimizer changes.

Tasks:

- [x] Add layer profile reports for reference vs candidate width/depth/area curves.
- [x] Detect candidate under-scale or axis compression from layer bounds.
- [x] Add optional voxel smoothing presets for sculpture imports.
- [x] Improve ray voxelizer column filling near thin silhouettes.
- [x] Add contour cleanup to remove isolated protrusions per layer.
- [ ] Re-run queen comparison after each tuning change and track IoU, missing, and extra deltas.
- [x] Add layer-slice voxelizer that cuts the mesh per LEGO layer and fills projected contours.
- [x] Add optional Studio-style target footprint scaling before voxelization.
- [x] Add density sculpture mode with shell/base plus deterministic lattice infill.
- [x] Add ribbed internal support infill with staggered X/Z support lines and vertical posts.
- [x] Add Studio-like layer smoothing preset for filled layer holes, vertical layer gaps, and isolated protrusion cleanup.
- [x] Change layer-slice contour filling to union same-layer contours by default, reducing false holes from fragmented open OBJ slices.
- [x] Add `profile` smoothing preset for stricter layer cleanup:
  - remove small disconnected 2D islands per layer
  - fill layer holes before optimization
  - trim middle-layer spikes that do not agree with adjacent layer profiles

Acceptance criteria:

- [ ] Queen output has fewer visible holes and fewer isolated protrusions.
- [ ] Studio comparison IoU improves over the Phase 10 baseline.
- [ ] Layer-level extra/missing spikes are reduced in the lower and middle layers.

Latest Studio smoothing diagnostic:

- `voxelizer=slice`, target footprint `38x37`, solid, `voxel_smoothing=studio` IoU: `0.309009`, missing `571`, extra `13320`.
- Compared with unsmoothed solid (`0.309746`, missing `611`, extra `13143`), the Studio smoothing preset slightly reduces missing surface cells while preserving the layer-filled sculpture behavior.
- Interpretation: this is the better visual candidate when the priority is clean, layer-filled Studio-like surfaces. Density/rib modes are useful for reducing interior mass, but they can expose holes and support patterns on the visible model.

Latest contour union diagnostic:

- The slice voxelizer now uses union filling for same-layer contours by default.
- This intentionally favors continuous sculpture layers over preserving every mesh hole, because fragmented open OBJ contour loops can otherwise create false cutouts in the generated LEGO model.

Latest profile smoothing diagnostic:

- `voxel_smoothing=profile` is intended for visual sculpture cleanup when an open OBJ creates small floating layer islands or sharp one-layer spikes.
- It is stricter than `studio`, so it should be used for Studio-like sculpture imports before adding more brick-level optimizer complexity.
- Queen candidate: `outputs/ldr/queen_slice_profile_studio_palette_solid_60.ldr`.
- Comparison against `queen.io`: IoU `0.308884`, missing `580`, extra `13299`.
- Compared with the previous Studio-palette candidate (`0.308805`, missing `572`, extra `13330`), profile smoothing slightly reduces overfill and improves stability metrics, but does not solve the main shape mismatch by itself.
- Stability improved from average support ratio `0.7981` to `0.8203`; floating brick count dropped from `501` to `430`, and overhang risk count dropped from `81` to `65`.

## Phase 12: Studio Reference Brick Palette

Status: completed.

Purpose:

Match MakeYourBrick's candidate brick set to the actual parts observed in the user's Studio queen import before adding new part families. This keeps the comparison focused on voxel/profile quality instead of optimizer palette drift.

Reference finding:

- The inspected `queen.io` archive's primary `model.ldr` uses regular brick parts only.
- Plate parts such as `3020.dat`, `3021.dat`, `3022.dat`, and `3023.dat` were not present in the primary Studio output.
- Studio's queen output also did not use `3006.dat` 2x10, while MakeYourBrick's full palette did use it heavily.

Tasks:

- [x] Add a separate `studio` brick palette.
- [x] Keep the existing `full` palette for experimental conversions.
- [x] Expose `--brick-palette full|studio` in mesh and image CLIs.
- [x] Expose `brick_palette` in backend job requests.
- [x] Record the selected palette in optimizer reports.
- [x] Generate a queen candidate with `--brick-palette studio`.
- [x] Compare the new candidate against `queen.io`.
- [x] Decide whether plate support is needed only after a reference Studio output actually contains plate parts.

Acceptance criteria:

- [x] Studio-palette output contains no `3006.dat`.
- [x] The optimizer report records `"brick_palette": "studio"`.
- [x] Part distribution is closer to the Studio reference before further voxel/profile tuning.

Latest Studio palette diagnostic:

- Candidate: `outputs/ldr/queen_slice_union_studio_palette_solid_60.ldr`.
- `3006.dat` count changed from 554 in the full-palette candidate to 0 in the Studio-palette candidate.
- Studio reference `model.ldr` contains no plate parts in the inspected queen import, so plate support is deferred until a reference output actually uses plate families.
- Comparison against `queen.io`: IoU `0.308805`, missing `572`, extra `13330`.
- Interpretation: the palette is now less misleading, but the visible shape problem is still dominated by voxel layer profile and density/fill selection, not part availability.

## Phase 13: Exterior Rod Reduction

Status: completed.

Purpose:

Reduce the long horizontal rods visible in Stud.io when the layered optimizer uses 1x8 and 2x8 bricks on jagged sculpture boundaries.

Tasks:

- [x] Add boundary-aware scoring to penalize long bricks placed on layer footprint boundaries.
- [x] Add a `compact` brick palette that limits candidate spans to 4 studs:
  - `3010.dat` 1x4
  - `3001.dat` 2x4
  - `3622.dat` 1x3
  - `3002.dat` 2x3
  - `3004.dat` 1x2
  - `3003.dat` 2x2
  - `3005.dat` 1x1
- [x] Generate a queen candidate with `--brick-palette compact`.
- [x] Compare long-brick counts and visual stability against the Studio-palette candidate.

Acceptance criteria:

- [x] No generated brick has a footprint longer than 4 studs in compact mode.
- [x] The queen visual candidate no longer includes 1x8, 2x8, 1x6, or 2x6 parts.
- [x] Occupancy preservation tests still pass.

Latest compact palette diagnostic:

- Candidate: `outputs/ldr/queen_slice_profile_compact_60.ldr`.
- Comparison against `queen.io`: IoU `0.309010`, missing `558`, extra `13362`.
- Long parts removed from candidate output: `3007.dat`, `3008.dat`, `3009.dat`, and `2456.dat` are all 0.
- Part distribution now uses only 4-stud-or-shorter bricks: `3001.dat`, `3010.dat`, `3622.dat`, `3004.dat`, `3002.dat`, `3003.dat`, and `3005.dat`.
- Average support ratio improved to `0.8733`; brick count increased to `4080`, which is expected because compact mode prioritizes visual contour stability over part count reduction.

## Phase 14: Polished Surface Cleanup and Plate Readiness

Status: in progress.

Purpose:

Reduce remaining jagged surface noise after compact brick placement, and clarify the technical path for real plate support.

Reference finding:

- The inspected Studio queen `model.ldr` still contains no plate parts.
- Real plate support requires a vertical resolution change because a LEGO plate is one third of a brick height. The current voxel grid treats one Y layer as one full brick height, so replacing bricks with plates would create incorrect physical height unless the Y grid becomes plate-height based.

Tasks:

- [x] Add `polished` voxel smoothing preset.
- [x] Add 8-neighbor 2D layer contour smoothing.
- [x] Remove small layer noise after polished smoothing.
- [x] Keep backend and CLI validation in sync.
- [x] Add plate-height LDraw output mode.
- [x] Add plate-only optimizer palette:
  - `3020.dat` 2x4 plate
  - `3710.dat` 1x4 plate
  - `3021.dat` 2x3 plate
  - `3022.dat` 2x2 plate
  - `3023.dat` 1x2 plate
  - `3024.dat` 1x1 plate
- [x] Generate a queen candidate with `--voxel-smoothing polished --brick-palette compact`.
- [x] Generate a queen candidate with `--height-unit plate --brick-palette plates`.
- [x] Compare polished compact and plate-height outputs against the previous compact candidate.

Acceptance criteria:

- [x] Polished compact output is available for visual inspection.
- [x] Test suite passes with the new smoothing preset.
- [x] Plate-height mode uses plate part IDs and 8 LDU vertical spacing.

Latest plate-height diagnostic:

- Candidate: `outputs/ldr/queen_slice_polished_plates_60.ldr`.
- Plate parts used: `3020.dat`, `3710.dat`, `3021.dat`, `3022.dat`, `3023.dat`, and `3024.dat`.
- Occupancy shape changed from 60 brick-height layers to 180 plate-height layers.
- Output brick/plate count: `12091`.
- Studio comparison after plate footprint support: IoU `0.297795`, missing `300`, extra `14987`.
- Interpretation: plate mode proves the correct height model and part output path, but it greatly increases part count and overfill. It is best treated as an optional visual/detail mode, not the default Studio-like sculpture path yet.

Latest light smoothing diagnostic:

- Baseline IoU: `0.125026`, missing `4954`, extra `7846`.
- `voxel_smoothing=light` IoU: `0.125188`, missing `4952`, extra `7843`.
- Interpretation: light smoothing removes a few unsupported protrusions without changing scale. The main quality gap is still voxel fill/profile shape, not isolated spur cleanup alone.

Latest balanced ray-fill diagnostic:

- `ray_fill=balanced` IoU: `0.124726`, missing `4964`, extra `7801`.
- Interpretation: balanced odd-hit pairing reduces extra filled cells, but slightly lowers IoU on the queen sample. It remains an opt-in mode; default ray behavior stays `wide`.

Latest contour smoothing diagnostic:

- `voxel_smoothing=contour` IoU: `0.124838`, missing `4957`, extra `7844`.
- Profile hints still flag compressed width, compressed depth, and overfilled layers.
- Interpretation: local contour cleanup is not enough for the queen mismatch. The next correction needs profile-aware scale/axis handling or a different silhouette sampling strategy, not only per-layer smoothing.

Latest Studio-like slice and footprint diagnostics:

- `voxelizer=slice` IoU: `0.130286`, missing `4879`, extra `7831`.
- `voxelizer=slice`, target footprint `38x37` IoU: `0.309746`, missing `611`, extra `13143`.
- `voxelizer=slice`, target footprint `38x37`, shell wall `1` IoU: `0.167224`, missing `5034`, extra `3676`.
- `voxelizer=slice`, target footprint `38x37`, shell wall `2` IoU: `0.183744`, missing `4658`, extra `4782`.
- Interpretation: layer slicing plus explicit footprint scaling is the first major improvement. It fixes most of the missing reference footprint but overfills the interior, so the next Studio-like step is density/fill control rather than another axis fix.

Latest density fill diagnostics:

- `voxelizer=slice`, target footprint `38x37`, density mode `0.35` IoU: `0.227501`, missing `3795`, extra `6351`.
- `voxelizer=slice`, target footprint `38x37`, density mode `0.65` IoU: `0.254558`, missing `2957`, extra `8247`.
- Interpretation: density mode provides a controllable middle ground between shell and solid. On the queen sample, higher density recovers more reference cells but still does not beat full solid IoU because Studio's actual placement appears to use structured internal support/bridging, not simple uniform lattice infill.

Latest ribbed support diagnostics:

- `voxelizer=slice`, target footprint `38x37`, density `0.65`, ribs IoU: `0.254856`, missing `3109`, extra `7633`.
- `voxelizer=slice`, target footprint `38x37`, density `0.45`, ribs IoU: `0.242814`, missing `3725`, extra `5811`.
- Interpretation: ribbed support keeps a similar IoU to lattice at the same density while reducing extra cells. It is a better internal support direction than uniform lattice, but still needs reference-guided layer density selection or a brick-level support planner to match Studio more closely.
