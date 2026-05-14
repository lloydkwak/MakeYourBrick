# Architecture

MakeYourBrick is a staged OBJ-first image/mesh-to-LDraw pipeline. The stable production path is mesh-first: every real or generated object must become a triangle mesh before voxelization and LEGO conversion.

## Pipeline

```text
image
  -> Sam3DRunner command contract
  -> optional object mask
  -> raw SAM artifact preservation
  -> triangle mesh artifact (.obj preferred)
  -> mesh inspection
  -> mesh repair
  -> voxelization
  -> sculpture occupancy mode
  -> optional mesh color sampling
  -> LDraw color quantization
  -> brickification or layer-aware optimization
  -> LDraw .ldr output
  -> JSON reports
```

## Main Components

### AI Adapter

Location:

- `src/makeyourbrick/ai/sam3d_runner.py`
- `src/makeyourbrick/ai/sam3d_adapter.py`
- `scripts/image_to_ldr.py`
- `scripts/adapters/run_sam3d_objects_export.py`
- `scripts/adapters/sam3d_to_mesh.py`

The runner executes a configurable command template. The template can use `{image}`, `{mask}`, `{output}`, `{output_dir}`, and `{repo}` placeholders. The command must write a Trimesh-loadable triangle mesh to `{output}`.

The preferred SAM 3D Objects path is direct OBJ export from the upstream triangle mesh output. The wrapper can also export GLB when explicitly requested, but GLB is now treated as one supported mesh format rather than the default. Gaussian splat PLY files are preserved as debug artifacts only and are not accepted as the standard MakeYourBrick geometry input.

This design keeps the repository testable without installing SAM 3D or requiring a GPU.

### Mesh Processing

Location:

- `src/makeyourbrick/mesh/solidify.py`
- `src/makeyourbrick/mesh/inspect.py`
- `src/makeyourbrick/mesh/repair.py`
- `src/makeyourbrick/mesh/color_sampling.py`

The mesh module loads `.obj`, `.stl`, `.glb`, mesh `.ply`, and other Trimesh-supported triangle mesh formats. It can merge `trimesh.Scene` geometry into one mesh, inspect compatibility, and repair with explicit modes: `none`, `basic`, `manifold`, and `convex-hull`.

Meshes are oriented to the pipeline's Y-up coordinate system before voxelization. The default `auto` mode maps a clearly dominant longest axis, such as Z-up OBJ sculpture assets, to vertical Y so LDraw output is not laid on its side.

Color sampling currently supports nearest vertex color and nearest face color. Full UV texture sampling is not implemented yet.

### Voxelization

Location:

- `src/makeyourbrick/voxel/voxelize.py`
- `src/makeyourbrick/voxel/synthetic.py`

Meshes are voxelized with Trimesh. Voxel artifacts are saved as compressed `.npz` files containing:

- `occupancy`
- `color_ids`
- `rgb`
- `origin`
- `pitch`

The horizontal pitch is defined in studs from the selected longest-axis or base-size target. Before voxelization, the mesh Y dimension is scaled to the selected LDraw layer height: `20/24` for normal bricks and `20/8` for plates. This keeps Studio-like base-size imports from becoming too tall or too thin when LEGO's non-cubic brick proportions are written back to LDraw.

Two voxelizers are available:

- `surface`: Trimesh surface voxelization with optional fill, useful for watertight meshes.
- `ray`: vertical scanline filling that casts rays through each stud column, closer to Studio's layer-by-layer sculpture behavior and more useful for open OBJ/STL sculpture assets.
- `slice`: layer-by-layer section filling, currently the preferred sculpture path for OBJ assets.

### Color Quantization

Location:

- `src/makeyourbrick/brickify/colors.py`
- `data/ldraw/ldraw_colors.json`

RGB values are converted to CIELAB and matched to the closest LDraw palette color. The bundled palette is intentionally small and should be expanded before high-quality color output is expected.

### Brick Optimization

Location:

- `src/makeyourbrick/brickify/optimizer.py`
- `src/makeyourbrick/brickify/report.py`

The optimizer uses a deterministic greedy placement strategy with a Studio-like basic brick set:

```text
2x10 -> 2x8 -> 2x6 -> 2x4 -> 1x8 -> 2x3 -> 1x6 -> 1x4 -> 2x2 -> 1x3 -> 1x2 -> 1x1
```

It preserves occupancy and color boundaries. The optional `layered` optimizer places bricks layer by layer and scores candidates by area, support ratio, overhang penalty, and vertical seam alignment. Reports include stability metrics such as unsupported brick count, floating brick count, low-support brick count, overhang-risk brick count, connected component count, average support ratio, seam alignment score, and layer count.

### Sculpture Engine

Location:

- `src/makeyourbrick/voxel/sculpture.py`
- `src/makeyourbrick/sculpture/`

Sculpture conversion post-processes the voxel occupancy before brick placement:

- `solid`: keep the filled voxel model
- `shell`: keep surface voxels, optional wall thickness, and solid base layers
- `contour-shell`: keep per-layer outline walls, base fill, and sparse support columns
- `density`: keep shell/base plus deterministic interior infill

The `layered` sculpture engine separates `solid`, `shell`, `base`, `support`, and final `target` masks before brick placement. That mirrors the useful parts of Brickalize/Studio/BrickFormer-style sculpture conversion while keeping the implementation small and testable.

### LDraw Output

Location:

- `src/makeyourbrick/io/ldr_writer.py`

The writer emits LDraw line type 1 part references. It supports 0, 90, 180, and 270 degree rotations around the vertical axis.

Brick coordinates are converted to the LDraw part-center origin, so larger bricks cover the same voxel footprint as equivalent 1x1 bricks.

When `steps_by_layer` is enabled, the writer inserts `0 STEP` markers between vertical layers so LDraw viewers can show a layer-by-layer build sequence.

### Quality Fixtures

Location:

- `src/makeyourbrick/quality/mesh_samples.py`
- `scripts/make_ldraw_placement_fixture.py`
- `scripts/compare_mesh_samples.py`

Placement fixtures support Stud.io visual checks for the basic brick set. Mesh sample comparison generates sphere, bust-like, and object-like meshes, converts them through the production pipeline, and writes a JSON summary with brick counts and stability metrics.

## Directory Layout

```text
data/                   Input images, example meshes, LDraw palette
docs/                   Architecture, usage, environment, testing, references
outputs/                Generated artifacts, ignored except .gitkeep files
scripts/                CLI entry points
src/makeyourbrick/      Python package
tests/                  Automated test suite and fake SAM command
third_party/            External repos such as sam-3d-objects, ignored
```

### Backend and UI

Location:

- `src/makeyourbrick/server/`
- `apps/web/`

The backend exposes image upload, placeholder mask generation, job creation, job status, result, artifact download, and configuration endpoints. It defaults to a deterministic fake SAM runner for local development. In `sam3d` mode it requires `mask_id` and runs the configured SAM command template.

## Current Status

The local OBJ-first mesh-to-LDraw pipeline, web job flow, mesh inspection, repair reports, SAM adapter contract, and SAM 3D Objects export wrapper are implemented and tested. Real SAM 3D inference still needs to be run in a suitable GPU/Linux environment to validate the wrapper against the upstream model and record a real sample.
