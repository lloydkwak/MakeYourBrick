# Native BrickFormer-Style Upgrade

This note records the clean-room algorithm changes taken from studying BrickFormer's public workflow and source structure. The goal is not to embed BrickFormer, but to move MakeYourBrick's native converter toward the same modeling assumptions.

## Observed BrickFormer Concepts

- Input control is X/Z resolution. The model height is derived after a LEGO brick-height correction.
- The slicer creates a per-layer color map from mesh/triangle intersections. It does not start from a fully filled solid volume.
- Placement enumerates candidate brick footprints over each layer.
- A candidate can cover both colored surface cells and nearby empty cells, as long as enough of the footprint covers the color map.
- Candidate reward combines brick size, color coverage, color homogeneity, same-layer neighbors, previous-layer connectivity/support, and proximity to previous real surface.
- Pure empty-area filling is only allowed in tightly enclosed holes, not as a whole-model interior fill.
- The default brick catalog is normal brick-height rectangular bricks, not plate-height output.
- Export is layer ordered, so LDraw `0 STEP` remains the native instruction primitive.

## Native Decisions

- Keep the Python pipeline and LDR writer.
- Keep `solid`, `shell`, `contour-shell`, and `density` as explicit experimental modes.
- Add `slice-surface` voxelization for contour cells only as an experimental lightweight path.
- Add `brickformer` sculpture mode for surface slice targets as an experimental lightweight path.
- Add partial-coverage layered placement for surface targets.
- Keep `--studio-import-preset` on direct OBJ loading, filled layer slices, a thick wall target, normal-height Studio bricks, and exact layer placement, because that is closer to the measured Studio reference than raw surface-only, fully solid, or support-column placement.

## Current Studio Import Preset

```text
voxelizer: slice
sculpture_engine: layered
sculpture_mode: contour-shell
wall_thickness: 3
base_thickness: 0
support_spacing: 0
optimizer: layered
brick_palette: studio
height_unit: brick
voxel_smoothing: polished
color_strategy: majority
repair_mode: none
steps_by_layer: true
```

## Expected Effect

- Filled, readable layer-by-layer wall output rather than a sparse surface cage, fully solid mass, or visible support-column model.
- No default plate-height output, so flat plates are not overused.
- More stable large normal bricks than pure one-cell contour placement.
- Experimental `slice-surface + brickformer` remains available for lightweight tests but is not the default.

## Remaining Gaps

- The native solver is CPU based and simpler than BrickFormer's CUDA exhaustive reward evaluator.
- The current partial-coverage reward does not yet implement BrickFormer's proximity-map spreading exactly.
- The brick catalog still lacks non-rectangular corner bricks used by BrickFormer.
- Surface smoothness still depends on source mesh quality and `slice-surface` contour tolerance.
