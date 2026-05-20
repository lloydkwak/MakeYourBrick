# MakeYourBrick Web App

This is the browser UI for the local MakeYourBrick pipeline.

## Flow

- upload an image
- select the object with positive/negative points or a box
- preview the SAM2 mask overlay
- run SAM 3D reconstruction
- inspect the raw GLB in the right preview panel
- download the generated LDR

## Running

The normal entrypoint is the Docker backend:

```text
http://127.0.0.1:8000
```

The FastAPI app serves this directory as static files, so no frontend package
install is required.

For local frontend/backend development without Docker:

```bash
python -m uvicorn makeyourbrick.server.main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

## Preview

The right panel displays the raw SAM 3D `.glb` with `glb-viewer.js`. The viewer
uses WebGL when available and falls back to a 2D canvas renderer if the browser
does not provide a WebGL context. LDR files are not previewed in the browser;
they are downloaded and inspected in BrickLink Studio or another LDraw viewer.

## Artifacts

Completed jobs expose:

- `3D model`: raw SAM GLB
- `LDR`: final LDraw model
