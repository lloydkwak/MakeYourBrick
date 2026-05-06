# MakeYourBrick

Image-to-LEGO 3D conversion pipeline for generating LDraw `.ldr` files from images or mesh artifacts.

See [docs/image_to_lego_3d_plan.md](docs/image_to_lego_3d_plan.md) for the concrete architecture, directory structure, file responsibilities, tech stack, and implementation milestones.

## Phase 1 Synthetic LDraw

Generate a simple 1x1-brick LDraw model from a synthetic voxel box:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 3 2 --color 16 --output outputs/ldr/synthetic_box.ldr
```

Run the current verification suite:

```bash
python -m compileall src scripts
python -m pytest
```

## Phase 2 Mesh LDraw

Convert an existing mesh into a 1x1-brick LDraw model:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 24 --output outputs/ldr/mesh_output.ldr
```

The mesh path can point to formats supported by Trimesh, including `.stl`, `.obj`, and `.glb`.
