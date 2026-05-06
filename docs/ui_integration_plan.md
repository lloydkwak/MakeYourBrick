# UI Integration Plan: Image Upload, Object Selection, and LEGO Conversion

This document describes the planned user interface for MakeYourBrick.

The UI will let a user upload an image, select the object to convert, run the image/mesh-to-LEGO pipeline, and download or inspect the generated LDraw output and reports.

## Product Goal

Provide an interactive workflow:

```text
upload image
  -> select target object
  -> preview segmentation mask
  -> run 3D reconstruction
  -> convert to LEGO bricks
  -> inspect result and report
  -> export .ldr
```

## UX Principles

- The first screen should be the actual tool, not a marketing page.
- The interface should be clear and operational, with minimal decorative UI.
- The user should always know which pipeline step is running.
- Intermediate artifacts should be visible when useful.
- Failures should be actionable: missing SAM, invalid mesh, empty voxel grid, too many bricks, and unsupported output format should all produce clear messages.

## Core User Flow

### Step 1: Upload Image

User actions:

- drag and drop an image
- or choose a local file

Accepted formats:

- `.png`
- `.jpg`
- `.jpeg`
- `.webp`

UI state:

- image preview
- basic metadata: width, height, file size
- clear/reset button

Backend output:

```text
data/input_images/<session_id>/input.png
```

### Step 2: Select Object

The UI should support SAM-style target selection.

Initial interaction modes:

- point click: user clicks inside the target object
- box selection: user drags a bounding box around the object
- optional negative click: user marks background or wrong object area

Planned controls:

- mode toggle: point / box
- undo last point
- clear selection
- preview mask

Frontend data model:

```json
{
  "image_id": "session-id",
  "positive_points": [[x, y]],
  "negative_points": [[x, y]],
  "box": [x0, y0, x1, y1]
}
```

Backend output:

```text
data/masks/<session_id>/mask.png
```

### Step 3: Segmentation Preview

Purpose:

- confirm that the selected object is correct before running expensive 3D reconstruction

UI:

- original image with translucent mask overlay
- mask visibility toggle
- accept mask
- refine selection

Backend:

- For the first UI milestone, this can use a stub mask generator or manual polygon/box mask.
- Later, this should call a SAM/SAM 2 segmentation backend.

### Step 4: Configure LEGO Output

Options:

- target longest studs
- default LDraw color
- sample mesh colors
- optimize bricks
- voxel fill on/off
- report generation

Suggested defaults:

```json
{
  "target_studs": 48,
  "sample_colors": true,
  "optimize": true,
  "fill": true,
  "default_color_id": 16
}
```

### Step 5: Run Pipeline

Pipeline stages displayed in the UI:

1. image segmentation
2. 3D reconstruction
3. mesh inspection
4. mesh repair
5. voxelization
6. color quantization
7. brick optimization
8. LDraw export

Each stage should expose:

- status: pending / running / completed / failed
- elapsed time
- short log message
- artifact path if available

### Step 6: Results

Result panel:

- generated `.ldr`
- optimizer report summary
- brick count
- reduction percentage
- part counts
- color counts
- warnings

Possible preview levels:

- minimum: text summary and artifact links
- intermediate: voxel/brick count visualization
- advanced: browser 3D preview with Three.js

## Recommended Tech Stack

### Frontend

Recommended first implementation:

- React
- Vite
- TypeScript
- canvas overlay for image selection
- lightweight state management with React state or Zustand

Why:

- fast local development
- strong image/canvas interaction support
- easy integration with a Python backend API

### Backend

Recommended first implementation:

- FastAPI
- Uvicorn
- Pydantic request/response models
- background task queue for long-running conversion jobs

Why:

- Python-native integration with existing MakeYourBrick modules
- straightforward file upload support
- simple JSON API
- async job status endpoints

### Job Execution

First milestone:

- local background tasks
- in-memory job registry

Later:

- Redis + RQ/Celery
- persistent job database

## Proposed Repository Structure

```text
apps/
  web/
    package.json
    index.html
    src/
      App.tsx
      api.ts
      components/
        ImageUploader.tsx
        SelectionCanvas.tsx
        PipelineControls.tsx
        JobProgress.tsx
        ResultPanel.tsx
      styles.css
  api/
    main.py
    schemas.py
    jobs.py
    storage.py
```

Alternative:

```text
src/makeyourbrick/server/
  main.py
  schemas.py
  jobs.py
  storage.py
```

The first structure is cleaner if the UI grows into a real app. The second structure is simpler if this stays a Python-first course project.

## API Design

### Upload Image

```http
POST /api/images
```

Request:

- multipart file

Response:

```json
{
  "image_id": "uuid",
  "image_url": "/api/images/uuid/file",
  "width": 1024,
  "height": 768
}
```

### Submit Selection

```http
POST /api/images/{image_id}/selection
```

Request:

```json
{
  "positive_points": [[320, 240]],
  "negative_points": [],
  "box": null
}
```

Response:

```json
{
  "mask_id": "uuid",
  "mask_url": "/api/masks/uuid/file",
  "status": "completed"
}
```

### Start Conversion

```http
POST /api/jobs
```

Request:

```json
{
  "image_id": "uuid",
  "mask_id": "uuid",
  "target_studs": 48,
  "sample_colors": true,
  "optimize": true,
  "fill": true,
  "default_color_id": 16
}
```

Response:

```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

### Poll Job

```http
GET /api/jobs/{job_id}
```

Response:

```json
{
  "job_id": "uuid",
  "status": "running",
  "stage": "voxelization",
  "progress": 0.52,
  "message": "Voxelizing cleaned mesh"
}
```

### Get Result

```http
GET /api/jobs/{job_id}/result
```

Response:

```json
{
  "ldr_url": "/api/jobs/uuid/files/ldr",
  "report_url": "/api/jobs/uuid/files/report",
  "raw_mesh_url": "/api/jobs/uuid/files/raw_mesh",
  "brick_count": 117,
  "reduction_percent": 83.9506,
  "warnings": []
}
```

## Backend Integration Plan

### Milestone UI-1: Local Web Shell

Purpose:

- Build the image upload and selection UI without running SAM.

Tasks:

1. Create React/Vite app.
2. Add image uploader.
3. Add canvas overlay.
4. Implement point and box selection.
5. Show selection payload JSON.
6. Add static mock mask overlay.

Done criteria:

- User can upload an image.
- User can click/select an object target.
- UI records coordinates correctly.

Implementation status:

- Implemented as a static local web shell under `apps/web`.
- Open `apps/web/index.html` in a browser.
- Supports file upload, drag and drop, point selection, box selection, positive/negative labels, mock mask overlay, LEGO settings preview, and JSON export.

### Milestone UI-2: FastAPI Backend

Purpose:

- Persist uploaded images and expose job-oriented API.

Tasks:

1. Add FastAPI app.
2. Implement image upload endpoint.
3. Store images under `outputs/ui_sessions/<session_id>/`.
4. Serve uploaded image files.
5. Add selection endpoint.
6. Return a placeholder mask.

Done criteria:

- Frontend uploads image to backend.
- Backend returns stable image ID.
- Selection data is persisted.

Implementation status:

- Implemented under `src/makeyourbrick/server`.
- Provides health, image upload, image file serving, selection submission, and placeholder mask serving endpoints.
- Stores session artifacts under `outputs/ui_sessions` by default.
- The static web shell can sync uploads and selections to the backend through the `Sync Backend` button.

### Milestone UI-3: Pipeline Job Stub

Purpose:

- Connect UI to a fake conversion job.
- Validate the end-to-end browser/API/pipeline contract before real SAM 3D is installed.

Tasks:

1. Add job registry.
2. Add background job execution.
3. Use fake SAM command to generate a colored box mesh.
4. Run existing `run_from_image()` or `image_to_ldr` equivalent.
5. Return `.ldr` and report URLs.
6. Replace the frontend-only mock run with a real `/api/jobs` call.
7. Poll job status until `completed` or `failed`.
8. Show artifact links for LDR, report, and raw mesh.

Done criteria:

- User can upload image, select object, click convert, and receive `.ldr` output.
- No real SAM dependency yet.

Implementation status:

- Implemented as a local FastAPI job stub.
- `POST /api/jobs` validates the uploaded image and optional placeholder mask, creates an in-memory job record, and starts a background conversion task.
- The background task uses `FakeSamMeshRunner` to create a deterministic colored triangle mesh, then calls the existing `run_from_image()` pipeline.
- Job artifacts are stored below `outputs/ui_sessions/<image_id>/jobs/<job_id>/`.
- `GET /api/jobs/{job_id}` returns status, stage, progress, and message.
- `GET /api/jobs/{job_id}/result` returns generated artifact URLs and optimizer summary values.
- `GET /api/jobs/{job_id}/files/{kind}` serves `ldr`, `report`, `raw_mesh`, `cleaned_mesh`, and `voxels`.
- The static web shell now uses `Run Conversion` to upload/sync if needed, start a backend job, poll status, and display artifact links.

Current limitation:

- The fake SAM runner ignores the selection mask. It exists only to test the contract between UI, backend jobs, and the existing LEGO conversion pipeline.

### Milestone UI-3.5: Placeholder Segmentation Upgrade

Purpose:

- Improve pre-SAM UX validation without adding the real segmentation model yet.

Tasks:

1. Make point-based masks more object-like than simple circles.
2. Blend box and point prompts into a single placeholder mask.
3. Let the frontend display the backend-generated mask overlay instead of only the canvas-local preview.
4. Preserve positive and negative prompt semantics.

Done criteria:

- The mask preview is stable enough to validate upload, prompt, sync, and conversion UX.
- The mask API shape can be reused by real segmentation later.

Implementation status:

- Implemented as a pre-SAM backend mask preview.
- The placeholder mask generator now blends box and positive point prompts into a smoother object-like region.
- Negative points cut holes from the placeholder mask.
- The static web shell loads the backend-generated mask image after `Sync Backend` or `Run Conversion` and draws it as the canvas overlay.
- Editing the selection invalidates stale mask, job, and result artifacts while keeping the uploaded backend image session.

Current limitation:

- This is still a deterministic prompt visualization, not semantic segmentation. It validates UI/API behavior before a real SAM image predictor is attached.

### Milestone UI-3.6: Mesh Inspection API

Purpose:

- Add early automated validation for future SAM 3D outputs.

Tasks:

1. Add `src/makeyourbrick/mesh/inspect.py`.
2. Add `scripts/inspect_mesh.py`.
3. Report triangle count, vertex count, watertightness, bounds, visual/color availability, and voxelization readiness.
4. Attach mesh inspection output to job reports or expose it through `/api/jobs/{job_id}/files/mesh_inspect`.

Done criteria:

- Any generated mesh can be checked before voxelization.
- Future real SAM adapter failures become diagnosable from job artifacts.

### Milestone UI-3.7: Real SAM Adapter Preparation

Purpose:

- Prepare the boundary where real SAM 3D Objects will replace the fake runner.

Tasks:

1. Add `scripts/adapters/sam3d_to_mesh.py`.
2. Discover actual SAM output files and formats.
3. Confirm whether output is triangle mesh, point cloud, Gaussian splat, or another representation.
4. Export triangle mesh directly when possible.
5. Design fallback conversion when SAM returns point clouds or splats.

Done criteria:

- The real adapter can satisfy the same runner contract as `FakeSamMeshRunner.generate(image_path, output_path)`.

### Milestone UI-3.8: Mesh Repair Modes

Purpose:

- Make AI-generated mesh cleanup explicit and testable.

Tasks:

1. Add repair mode options: `none`, `basic`, `manifold`, `convex-hull`.
2. Include repair mode in pipeline config and job request.
3. Generate repair reports.
4. Add open mesh fixtures and tests.

Done criteria:

- The pipeline can explain how it repaired or approximated invalid SAM meshes.

### Milestone UI-3.9: Stud.io/LDraw Visual Verification

Purpose:

- Confirm that optimized brick placement is visually correct in real LDraw-compatible tools.

Tasks:

1. Check origin and rotation behavior for `3001.dat`, `3010.dat`, `3003.dat`, `3004.dat`, and `3005.dat`.
2. Compare generated output in LDraw and Stud.io.
3. Add a part offset table if larger bricks need origin correction.
4. Document verified part transforms.

Done criteria:

- Large optimized bricks align correctly when opened in Stud.io/LDraw.

### Milestone UI-4: Real Segmentation Backend

Purpose:

- Replace placeholder selection/mask behavior with SAM-style segmentation.

Options:

- SAM 2 / Segment Anything image predictor
- External segmentation service
- SAM 3D Objects integrated segmentation if upstream exposes it cleanly

Done criteria:

- User clicks object.
- Backend returns a meaningful object mask.
- User can refine selection.

### Milestone UI-5: Real SAM 3D Backend

Purpose:

- Use accepted mask/selection to drive real 3D object reconstruction.

Tasks:

1. Pass image and selection/mask to the SAM 3D adapter.
2. Generate raw mesh.
3. Inspect mesh.
4. Repair mesh if needed.
5. Convert to LDraw.
6. Stream progress to UI.

Done criteria:

- A real user-selected object becomes a LEGO `.ldr`.

## UI State Machine

```text
idle
  -> image_uploaded
  -> selecting_object
  -> mask_preview
  -> configuring
  -> queued
  -> running
  -> completed
  -> failed
```

Failure states:

- upload_failed
- segmentation_failed
- reconstruction_failed
- mesh_invalid
- voxelization_failed
- export_failed

## Artifact Layout for UI Sessions

```text
outputs/ui_sessions/<session_id>/
  input/
    image.png
  selection/
    selection.json
    mask.png
  meshes/
    raw_model.glb
    cleaned_model.glb
  voxels/
    model_voxels.npz
  ldr/
    output.ldr
  reports/
    optimizer_report.json
    mesh_inspect.json
  logs/
    pipeline.log
```

## Main Technical Risks

- Real segmentation and real SAM 3D may need separate model environments.
- Long-running GPU jobs require progress reporting and cancellation.
- Large images and large voxel grids can create very slow jobs.
- Browser 3D preview of large LDraw outputs may be expensive.
- The selected object mask may not align with the generated 3D mesh.

## Recommended Next Step

Start with **Milestone UI-1: Local Web Shell**.

Do not wire real SAM yet. First build a polished image upload and object selection interface with a coordinate payload that the backend can later consume.
