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
- `scipy`
- `trimesh`
- `Pillow`
- `fastapi`
- `pydantic`
- `uvicorn`
- `python-multipart`
- `pytest`
- `ruff`

## SAM 3D

SAM 3D Objects remains external:

```text
third_party/sam-3d-objects
```

Do not commit that checkout. The MakeYourBrick runner only requires a command template that writes a triangle mesh to `{output}`.

See [Local SAM 3D Objects Setup](sam3d_local_setup.md) for the recommended
local checkout, checkpoint, and backend configuration flow.

## Generated Files

Generated artifacts belong under:

```text
outputs/
```

Only `.gitkeep` placeholders should be versioned there.
