# MakeYourBrick Web App

This is the local MakeYourBrick image-to-LDraw interface. The layout is inspired
by modern AI playground flows: upload an image, click or box-select the target
object, run the local backend job, and preview the generated LDR artifact.

## Run

Open `apps/web/index.html` in a browser.

No frontend package install or dev server is required.

## Backend

Run the FastAPI backend:

```bash
python -m uvicorn makeyourbrick.server.main:app --app-dir src --reload
```

The UI defaults to:

```text
http://127.0.0.1:8000
```

## Flow

- Upload or drag an image into the start panel.
- Use point or box selection to mark the object.
- Press `Generate LDR`.
- The backend creates the mesh, voxel target, LDR file, and report.
- The UI shows artifact links and a lightweight isometric LDR preview.

The preview is intentionally lightweight and browser-native. BrickLink Studio or
another LDraw viewer remains the source of truth for final visual inspection.

## SAM Mode

By default the backend can run with the fake mesh runner for local UI testing.
When configured with `MAKEYOURBRICK_RUNNER_MODE=sam3d`, the same UI sends the
selected mask id to the real SAM command path.
