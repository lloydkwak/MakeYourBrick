from __future__ import annotations

from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError

from makeyourbrick.server.jobs import JobRegistry, run_pipeline_job, to_status_response
from makeyourbrick.server.masks import create_placeholder_mask
from makeyourbrick.server.schemas import (
    HealthResponse,
    ImageUploadResponse,
    JobRequest,
    JobResultResponse,
    JobStatusResponse,
    SelectionRequest,
    SelectionResponse,
)
from makeyourbrick.server.storage import SessionStorage


def create_app(storage: SessionStorage | None = None, registry: JobRegistry | None = None) -> FastAPI:
    app = FastAPI(title="MakeYourBrick API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.storage = storage or SessionStorage()
    app.state.jobs = registry or JobRegistry()

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    @app.post("/api/images", response_model=ImageUploadResponse)
    async def upload_image(file: UploadFile = File(...)) -> ImageUploadResponse:
        try:
            image_id, path, image = await app.state.storage.save_upload(file)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except UnidentifiedImageError as error:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.") from error
        app.state.storage.write_manifest(
            image_id,
            {
                "image_id": image_id,
                "filename": file.filename,
                "image_path": str(path),
                "width": image.width,
                "height": image.height,
            },
        )
        return ImageUploadResponse(
            image_id=image_id,
            image_url=f"/api/images/{image_id}/file",
            width=image.width,
            height=image.height,
            filename=file.filename or path.name,
        )

    @app.get("/api/images/{image_id}/file")
    def get_image_file(image_id: str) -> FileResponse:
        try:
            path = app.state.storage.image_path(image_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return FileResponse(path)

    @app.post("/api/images/{image_id}/selection", response_model=SelectionResponse)
    def submit_selection(image_id: str, selection: SelectionRequest) -> SelectionResponse:
        try:
            image_path = app.state.storage.image_path(image_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        image = Path(image_path)
        with ImageResponseContext(image) as opened:
            mask_id = app.state.storage.new_id()
            mask_path = app.state.storage.mask_path(image_id, mask_id)
            create_placeholder_mask(opened.size, selection, mask_path)
        app.state.storage.save_selection(image_id, mask_id, selection)
        return SelectionResponse(
            image_id=image_id,
            mask_id=mask_id,
            mask_url=f"/api/masks/{mask_id}/file?image_id={image_id}",
            status="completed",
        )

    @app.get("/api/masks/{mask_id}/file")
    def get_mask_file(mask_id: str, image_id: str) -> FileResponse:
        path = app.state.storage.mask_path(image_id, mask_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Mask not found: {mask_id}")
        return FileResponse(path, media_type="image/png")

    @app.post("/api/jobs", response_model=JobStatusResponse)
    def create_job(request: JobRequest, background_tasks: BackgroundTasks) -> JobStatusResponse:
        try:
            app.state.storage.image_path(request.image_id)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        if request.mask_id is not None and not app.state.storage.mask_path(request.image_id, request.mask_id).exists():
            raise HTTPException(status_code=404, detail=f"Mask not found: {request.mask_id}")
        job_id = app.state.storage.new_id()
        record = app.state.jobs.create(request.image_id, job_id)
        background_tasks.add_task(run_pipeline_job, job_id, request, app.state.storage, app.state.jobs)
        return to_status_response(record)

    @app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
    def get_job(job_id: str) -> JobStatusResponse:
        try:
            record = app.state.jobs.get(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from error
        return to_status_response(record)

    @app.get("/api/jobs/{job_id}/result", response_model=JobResultResponse)
    def get_job_result(job_id: str) -> JobResultResponse:
        try:
            record = app.state.jobs.get(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from error
        if record.status == "failed":
            raise HTTPException(status_code=500, detail=record.error or "Job failed")
        if record.result is None:
            raise HTTPException(status_code=409, detail=f"Job is not completed: {record.status}")
        return record.result

    @app.get("/api/jobs/{job_id}/files/{kind}")
    def get_job_file(job_id: str, kind: str) -> FileResponse:
        try:
            record = app.state.jobs.get(job_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}") from error
        if kind not in record.paths:
            raise HTTPException(status_code=404, detail=f"Artifact not found: {kind}")
        path = record.paths[kind]
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Artifact file missing: {kind}")
        if kind in {"report", "mesh_inspect", "repair_report"}:
            return FileResponse(path, media_type="application/json")
        if kind == "ldr":
            return FileResponse(path, media_type="text/plain")
        return FileResponse(path)

    return app


class ImageResponseContext:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.image = None

    def __enter__(self):
        self.image = Image.open(self.path)
        self.image.load()
        return self.image

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self.image is not None:
            self.image.close()


app = create_app()
