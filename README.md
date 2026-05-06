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

## Phase 3 Color Quantization

Convert a mesh with a constant RGB color that is quantized to the nearest LDraw color:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 24 --rgb 242 205 55 --output outputs/ldr/yellow_mesh_output.ldr
```

The command above maps LEGO yellow RGB `(242, 205, 55)` to LDraw color ID `14`.

## Phase 4 Brick Optimization

Generate an optimized synthetic model by merging voxels into larger bricks:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 1 2 --color 16 --output outputs/ldr/optimized_box.ldr --optimize
```

Convert a mesh with greedy brick optimization enabled:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 8 --output outputs/ldr/mesh_optimized_phase4.ldr --optimize
```

## Phase 4.5 Mesh Color Sampling and Reports

Sample vertex or face colors from a mesh and write an optimizer report:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample_colored.ply --target-studs 8 --sample-colors --optimize --report outputs/reports/mesh_report.json --output outputs/ldr/sampled_color_mesh.ldr
```

The report includes occupied voxel count, input/output brick counts, reduction percentage, part counts, and color counts.
