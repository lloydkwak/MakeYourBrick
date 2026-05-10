# Architecture

MakeYourBrick is a staged image/mesh-to-LDraw pipeline. The stable production path is mesh-first: every real or generated object must become a triangle mesh before voxelization and LEGO conversion.

## Pipeline

```text
image
  -> Sam3DRunner command contract
  -> optional object mask
  -> raw SAM artifact preservation
  -> triangle mesh artifact (.glb preferred)
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

The preferred SAM 3D Objects path is direct GLB export from the upstream inference output. The wrapper falls back to exporting `output["mesh"][0]` through Trimesh when a GLB object is not available. Gaussian splat PLY files are preserved as debug artifacts only and are not accepted as the standard MakeYourBrick geometry input.

This design keeps the repository testable without installing SAM 3D or requiring a GPU.

### Mesh Processing

Location:

- `src/makeyourbrick/mesh/solidify.py`
- `src/makeyourbrick/mesh/inspect.py`
- `src/makeyourbrick/mesh/repair.py`
- `src/makeyourbrick/mesh/color_sampling.py`

The mesh module loads `.stl`, `.obj`, `.glb`, mesh `.ply`, and other Trimesh-supported triangle mesh formats. It can merge `trimesh.Scene` geometry into one mesh, inspect compatibility, and repair with explicit modes: `none`, `basic`, `manifold`, and `convex-hull`.

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

### Color Quantization

Location:

- `src/makeyourbrick/brickify/colors.py`
- `data/ldraw/ldraw_colors.json`

RGB values are converted to CIELAB and matched to the closest LDraw palette color. The bundled palette is intentionally small and should be expanded before high-quality color output is expected.

### Brick Optimization

Location:

- `src/makeyourbrick/brickify/optimizer.py`
- `src/makeyourbrick/brickify/report.py`

The optimizer uses a deterministic greedy placement strategy:

```text
2x4 -> 1x4 -> 2x2 -> 1x2 -> 1x1
```

It preserves occupancy and color boundaries. The optional `layered` optimizer scores candidate bricks by area, support ratio, overhang penalty, and vertical seam alignment. Reports include stability metrics such as unsupported brick count, floating brick count, average support ratio, seam alignment score, and layer count.

### Sculpture Mode

Location:

- `src/makeyourbrick/voxel/sculpture.py`

Sculpture mode post-processes the voxel occupancy before brick placement:

- `solid`: keep the filled voxel model
- `shell`: keep surface voxels, optional wall thickness, and solid base layers

This mirrors the useful parts of Studio-style sculpture import while keeping the original voxel artifact available for inspection.

### LDraw Output

Location:

- `src/makeyourbrick/io/ldr_writer.py`

The writer emits LDraw line type 1 part references. It supports 0, 90, 180, and 270 degree rotations around the vertical axis.

When `steps_by_layer` is enabled, the writer inserts `0 STEP` markers between vertical layers so LDraw viewers can show a layer-by-layer build sequence.

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

The local mesh-to-LDraw pipeline, web job flow, mesh inspection, repair reports, SAM adapter contract, and SAM 3D Objects export wrapper are implemented and tested. Real SAM 3D inference still needs to be run in a suitable GPU/Linux environment to validate the wrapper against the upstream model and record a real sample.
