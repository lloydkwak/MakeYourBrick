# Studio-Style Sculpture Layer Fill

This document records the current native target for MakeYourBrick's `--studio-import-preset`.

## Public Studio Behavior

BrickLink Studio's public help describes `File | Import | Import 3D Model...` as a sculpture workflow for OBJ/STL files. The sculpture dialog exposes:

- `Base Size`: maximum horizontal dimension, with the other dimensions scaled proportionally.
- `Wall Thickness`: wall width in studs. Studio may build thicker if needed.
- `Base Thickness`: number of lower layers that are completely filled.
- `Bricks`: allowed brick choices, including a 1x1-only option or selected brick buttons.
- `Color`: layer colors or OBJ material/texture colors.
- `Orientation`: source model up-axis correction.
- Import options to put each layer into its own step.

The same help page states that Studio builds the sculpture layer by layer in the viewport. See:

- https://studiohelp.bricklink.com/hc/en-us/articles/6508264220183-Sculpture
- https://studiohelp.bricklink.com/hc/en-us/articles/6502277722647-Import-formats

## Native Interpretation

Studio does not publish the exact internal algorithm, so MakeYourBrick uses a clean-room approximation:

```text
OBJ/STL mesh
  -> orient to Y-up
  -> choose pitch from Base Size / max XZ footprint
  -> slice mesh at each LEGO brick-height layer
  -> project section contours to the X/Z stud grid
  -> fill the 2D section footprint for each layer
  -> close small contour gaps and remove small noisy components
  -> keep the configured wall thickness from each filled layer
  -> place normal-height Studio brick candidates per wall layer
  -> insert 0 STEP between layers
```

## Current Preset

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
steps_by_layer: true
repair_mode: none
```

## Why Not Surface-Only

The experimental `slice-surface + brickformer` path keeps only cells close to mesh contour lines. It reduces part count, but on models like `queen.obj` it creates visible empty bands and cage-like holes. That is not the behavior users expect from Studio's sculpture import preview.

The default builds from filled 2D cross-sections, then keeps only a thick per-layer wall. Internal support columns are disabled by default because they produced visible vertical bands and do not match the provided Studio reference.

## Queen Baseline

With `queen.obj`, `base_size_studs=32`, and the current preset:

- target voxels: about `7020`
- output bricks: about `1794` with the current simple run tiler
- plate parts: `0`
- connected components: expected to be a connected wall shell for clean meshes
- average support ratio: reported per output

These values are from the simplified Studio wall path for `queen.obj` at `base_size_studs=32`.
