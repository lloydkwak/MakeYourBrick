# Architecture

MakeYourBrick is a staged image/mesh-to-LDraw pipeline. The stable production path is mesh-first: every real or generated object must become a triangle mesh before voxelization and LEGO conversion.

## Pipeline

```text
image
  -> Sam3DRunner command contract
  -> raw SAM artifact preservation
  -> triangle mesh artifact (.glb preferred)
  -> mesh inspection
  -> mesh repair
  -> voxelization
  -> optional mesh color sampling
  -> LDraw color quantization
  -> brickification
  -> optional greedy brick optimization
  -> LDraw .ldr output
  -> JSON reports
```

## Main Components

### AI Adapter

Location:

- `src/makeyourbrick/ai/sam3d_runner.py`
- `src/makeyourbrick/ai/sam3d_adapter.py`
- `scripts/image_to_ldr.py`
- `scripts/adapters/sam3d_to_mesh.py`

The runner executes a configurable command template. The template can use `{image}`, `{output}`, `{output_dir}`, and `{repo}` placeholders. The command must write a Trimesh-loadable triangle mesh to `{output}`.

SAM 3D Objects examples export Gaussian splat PLY files by default. These files are preserved as raw artifacts but are not accepted as the standard MakeYourBrick geometry input. The adapter classifies PLY artifacts as mesh PLY, Gaussian splat PLY, or point cloud PLY before deciding whether they can be converted to GLB.

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

It preserves occupancy and color boundaries. It does not yet evaluate real-world structural stability.

### LDraw Output

Location:

- `src/makeyourbrick/io/ldr_writer.py`

The writer emits LDraw line type 1 part references. It supports 0, 90, 180, and 270 degree rotations around the vertical axis.

## Directory Layout

```text
configs/                Default configuration
data/                   Input images, example meshes, LDraw palette
docs/                   Architecture, usage, environment, testing, references
outputs/                Generated artifacts, ignored except .gitkeep files
scripts/                CLI entry points
src/makeyourbrick/      Python package
tests/                  Automated test suite and fake SAM command
third_party/            External repos such as sam-3d-objects, ignored
```

## Current Status

The local mesh-to-LDraw pipeline, web job stub, mesh inspection, repair reports, and SAM adapter contract are implemented and tested. Real SAM 3D inference still needs to be run in a suitable GPU/Linux environment so the upstream mesh-producing command can be finalized.
