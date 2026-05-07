# MakeYourBrick

MakeYourBrick is a Python pipeline for converting a 2D image or 3D mesh into an LDraw `.ldr` LEGO model.

The local mesh-to-LDraw pipeline, web job stub, mesh inspection, mesh repair, and SAM adapter contract are implemented and tested. Real SAM 3D inference still requires a separate GPU/Linux setup and a verified mesh-producing command.

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
- local FastAPI backend and static web shell
- mesh inspection and repair reports
- SAM adapter contract with PLY artifact classification
- backend runner selection for fake, command, and SAM adapter modes

Current verification:

```bash
python -m compileall src scripts tests/fake_sam3d_command.py
python -m pytest
```

Latest local result: `76 passed`.

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
- [SAM 3D adapter](docs/sam3d_adapter.md)
- [SAM 3D mesh export TODO](docs/sam3d_mesh_export_todo.md)
- [Phase 6 TODO](docs/phase6_todo.md)
- [UI integration plan](docs/ui_integration_plan.md)
- [Roadmap and limitations](docs/roadmap.md)
- [References](docs/references.md)

## Important Limitations

- Real SAM 3D inference has not been executed in this repository.
- The SAM command must produce or expose a Trimesh-loadable triangle mesh. Gaussian splat PLY is preserved as a raw artifact but is not the default LEGO conversion input.
- Mesh repair is explicit and reported, but severe AI-generated meshes may still require approximation.
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
