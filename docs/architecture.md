# Architecture

MakeYourBrick is a staged image/mesh-to-LDraw pipeline. The current production path is mesh-first, with an image-to-mesh runner contract ready for SAM 3D Objects integration.

## Pipeline

```text
image
  -> Sam3DRunner command contract
  -> raw mesh artifact
  -> mesh cleanup
  -> voxelization
  -> optional mesh color sampling
  -> LDraw color quantization
  -> brickification
  -> optional greedy brick optimization
  -> LDraw .ldr output
  -> optional optimizer report JSON
```

## Main Components

### AI Adapter

Location:

- `src/makeyourbrick/ai/sam3d_runner.py`
- `scripts/image_to_ldr.py`

The runner executes a configurable command template. The template can use `{image}`, `{output}`, `{output_dir}`, and `{repo}` placeholders. The command must write a Trimesh-loadable mesh to `{output}`.

This design keeps the repository testable without installing SAM 3D or requiring a GPU.

### Mesh Processing

Location:

- `src/makeyourbrick/mesh/solidify.py`
- `src/makeyourbrick/mesh/color_sampling.py`

The mesh module loads `.stl`, `.obj`, `.glb`, `.ply`, and other Trimesh-supported formats. It can merge `trimesh.Scene` geometry into one mesh and performs basic cleanup. It does not currently guarantee true watertight manifold repair.

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

The local mesh-to-LDraw pipeline is implemented and tested. The SAM 3D integration layer is implemented as a command contract, but real SAM 3D inference has not been run in this repository.

