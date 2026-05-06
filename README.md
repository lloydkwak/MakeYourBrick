# MakeYourBrick

MakeYourBrick is a Python pipeline for converting a 2D image or 3D mesh into an LDraw `.ldr` LEGO model.

The local mesh-to-LDraw pipeline is implemented and tested. The image pipeline is wired through a SAM 3D Objects command contract, but real SAM 3D inference still requires a separate GPU setup and a mesh-producing adapter.

## Status

Implemented:

- synthetic voxel to LDraw
- mesh loading and cleanup
- mesh voxelization
- RGB to LDraw color quantization
- nearest vertex/face mesh color sampling
- greedy brick optimization
- LDraw output with basic rotations
- optimizer report JSON
- image-to-LDraw orchestration through a SAM command template

Current verification:

```bash
python -m compileall src scripts tests/fake_sam3d_command.py
python -m pytest
```

Latest local result: `52 passed`.

## Installation

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

For real SAM 3D Objects inference, see [docs/sam3d_manual_setup.md](docs/sam3d_manual_setup.md).

## Quick Usage

Optimized synthetic model:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 1 2 --color 16 --optimize --output outputs/ldr/optimized_box.ldr
```

Mesh to optimized LDraw:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 8 --optimize --output outputs/ldr/mesh_optimized.ldr
```

Colored mesh to optimized LDraw with report:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample_colored.ply --target-studs 8 --sample-colors --optimize --report outputs/reports/mesh_report.json --output outputs/ldr/sampled_color_mesh.ldr
```

Image to LDraw through a SAM command template:

```bash
python scripts/image_to_ldr.py --image data/input_images/sample.png --sam-repo third_party/sam-3d-objects --sam-command "<command that writes {output}>" --target-studs 48 --sample-colors --optimize --report outputs/reports/image_report.json --output outputs/ldr/image_output.ldr
```

## Documentation

- [Architecture](docs/architecture.md)
- [Usage](docs/usage.md)
- [Environment](docs/environment.md)
- [Testing](docs/testing.md)
- [SAM 3D manual setup](docs/sam3d_manual_setup.md)
- [Roadmap and limitations](docs/roadmap.md)
- [References](docs/references.md)

## Important Limitations

- Real SAM 3D inference has not been executed in this repository.
- The SAM command must produce a Trimesh-loadable triangle mesh, not only a Gaussian splat or point cloud.
- Mesh cleanup does not yet guarantee watertight manifold repair.
- Brick optimization reduces brick count but does not yet score real physical stability.
- LDraw part origins should be visually checked in Stud.io or another LDraw-compatible tool.

## References

This project is informed by:

- SAM 3D Objects: https://github.com/facebookresearch/sam-3d-objects
- Manifold: https://github.com/elalish/manifold
- Trimesh: https://github.com/mikedh/trimesh
- Brickalize: https://github.com/CreativeMindstorms/brickalize
- StableLego: https://github.com/intelligent-control-lab/StableLego
- Brick Optimization Builder: https://github.com/dzungpng/brick-optimization-builder
- LDraw file format: https://www.ldraw.org/article/218.html
