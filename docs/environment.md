# Environment

## Python

- Python 3.10+
- The local workspace has also been verified with Python 3.12.

## Install

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

## Core Dependencies

- `numpy`
- `trimesh`
- `Pillow`
- `fastapi`
- `uvicorn`
- `pytest`

## SAM 3D

SAM 3D Objects remains external:

```text
third_party/sam-3d-objects
```

Do not commit that checkout. The MakeYourBrick runner only requires a command template that writes a triangle mesh to `{output}`.

## Generated Files

Generated artifacts belong under:

```text
outputs/
```

Only `.gitkeep` placeholders should be versioned there.
