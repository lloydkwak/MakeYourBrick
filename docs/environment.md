# Environment

## Python

Recommended:

- Python 3.10+

The current local development environment has also been verified with Python 3.12.

## Local Pipeline Dependencies

Install:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

Core packages:

- `numpy`
- `scipy`
- `trimesh`
- `scikit-image`
- `Pillow`
- `PyYAML`
- `pytest`

## SAM 3D Dependencies

SAM 3D Objects is intentionally treated as an external dependency under:

```text
third_party/sam-3d-objects
```

Do not commit that external checkout.

The upstream SAM 3D setup currently targets Linux 64-bit with an NVIDIA GPU and significant VRAM. See `docs/sam3d_manual_setup.md` for details.

## Generated Artifacts

Generated artifacts belong under:

```text
outputs/
```

They are ignored by Git. Keep only `.gitkeep` placeholders in version control.

## Notes on PyTorch

`requirements.txt` includes PyTorch-related packages because real SAM 3D inference needs them. CUDA-specific PyTorch wheels may need to be installed manually depending on the target GPU machine.

