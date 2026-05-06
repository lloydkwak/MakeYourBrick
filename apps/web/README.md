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
- JSON export for the selection/config payload
- optional backend image/selection sync
- backend pipeline job stub execution
- result links for generated LDR, report, and raw mesh artifacts

## Scope

This shell does not call real SAM segmentation or SAM 3D Objects yet. `Run Conversion` calls the local FastAPI job stub, which generates a fake SAM mesh and runs the real MakeYourBrick conversion pipeline.

## Backend Workflow

Run the FastAPI backend:

```bash
python -m uvicorn makeyourbrick.server.main:app --app-dir src --reload
```

Then open this page, upload an image, make a selection, and press `Run Conversion`.
