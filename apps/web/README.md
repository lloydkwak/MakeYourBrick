# MakeYourBrick Web Shell

This is a local, static image upload and object selection shell for the MakeYourBrick UI milestones.

## Run

Open `apps/web/index.html` in a browser.

No package installation or dev server is required for this milestone.

## Features

- image upload by file picker or drag and drop
- point selection
- box selection
- positive and negative point labels
- translucent mock mask overlay
- selection payload preview in image coordinates
- LEGO conversion settings preview
- mesh or layer color strategy selection
- JSON export for the selection/config payload
- optional backend image/selection sync
- backend pipeline job execution
- result links for generated LDR, report, and raw mesh artifacts

## Scope

This shell does not run real segmentation in the browser. `Run Conversion` calls the local FastAPI job endpoint. By default the backend uses a fake SAM mesh for local development; when the backend is configured with `MAKEYOURBRICK_RUNNER_MODE=sam3d`, the same UI flow sends the selected mask id to the real SAM command path. Mesh color mode is the expected path for textured SAM GLB output.

## Backend Workflow

Run the FastAPI backend:

```bash
python -m uvicorn makeyourbrick.server.main:app --app-dir src --reload
```

Then open this page, upload an image, make a selection, and press `Run Conversion`.
