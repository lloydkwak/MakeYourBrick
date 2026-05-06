# Usage

Run commands from the repository root.

## Install

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

For lightweight local mesh tests, `torch` and SAM 3D are not required. For real SAM 3D inference, see `docs/sam3d_manual_setup.md`.

## Synthetic Voxel to LDraw

Generate a 1x1-brick synthetic box:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 3 2 --color 16 --output outputs/ldr/synthetic_box.ldr
```

Generate an optimized synthetic model:

```bash
python scripts/make_synthetic_ldr.py --shape box --size 4 1 2 --color 16 --optimize --output outputs/ldr/optimized_box.ldr
```

## Mesh to LDraw

Convert a mesh with default LDraw color:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 24 --output outputs/ldr/mesh_output.ldr
```

Convert a mesh with a constant RGB color quantized to LDraw:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 24 --rgb 242 205 55 --output outputs/ldr/yellow_mesh_output.ldr
```

Convert a colored mesh using nearest vertex/face color sampling:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample_colored.ply --target-studs 8 --sample-colors --output outputs/ldr/sampled_color_mesh.ldr
```

Convert with greedy brick optimization and write a report:

```bash
python scripts/mesh_to_ldr.py --mesh data/examples/sample_colored.ply --target-studs 8 --sample-colors --optimize --report outputs/reports/mesh_report.json --output outputs/ldr/sampled_color_mesh.ldr
```

## Image to LDraw

The image pipeline requires a SAM-compatible command template that writes a triangle mesh to `{output}`.

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "<command that writes {output}>" \
  --target-studs 48 \
  --sample-colors \
  --optimize \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

Supported command placeholders:

- `{image}`
- `{output}`
- `{output_dir}`
- `{repo}`

## Outputs

Generated files are ignored by Git:

- `outputs/meshes/`
- `outputs/voxels/`
- `outputs/ldr/`
- `outputs/reports/`

