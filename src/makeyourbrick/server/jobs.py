from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock

from makeyourbrick.ai.fake_runner import FakeSamMeshRunner
from makeyourbrick.pipeline import run_from_image
from makeyourbrick.server.schemas import JobRequest, JobResultResponse, JobStatusResponse
from makeyourbrick.server.storage import SessionStorage


@dataclass
class JobRecord:
    job_id: str
    image_id: str
    status: str = "queued"
    stage: str = "queued"
    progress: float = 0.0
    message: str = "Job queued"
    error: str | None = None
    paths: dict[str, Path] = field(default_factory=dict)
    result: JobResultResponse | None = None


class JobRegistry:
    def __init__(self) -> None:
        self._records: dict[str, JobRecord] = {}
        self._lock = Lock()

    def create(self, image_id: str, job_id: str) -> JobRecord:
        record = JobRecord(job_id=job_id, image_id=image_id)
        with self._lock:
            self._records[job_id] = record
        return record

    def get(self, job_id: str) -> JobRecord:
        with self._lock:
            if job_id not in self._records:
                raise KeyError(job_id)
            return self._records[job_id]

    def update(
        self,
        job_id: str,
        *,
        status: str | None = None,
        stage: str | None = None,
        progress: float | None = None,
        message: str | None = None,
        error: str | None = None,
        paths: dict[str, Path] | None = None,
        result: JobResultResponse | None = None,
    ) -> JobRecord:
        with self._lock:
            record = self._records[job_id]
            if status is not None:
                record.status = status
            if stage is not None:
                record.stage = stage
            if progress is not None:
                record.progress = max(0.0, min(1.0, progress))
            if message is not None:
                record.message = message
            if error is not None:
                record.error = error
            if paths is not None:
                record.paths.update(paths)
            if result is not None:
                record.result = result
            return record


def to_status_response(record: JobRecord) -> JobStatusResponse:
    return JobStatusResponse(
        job_id=record.job_id,
        image_id=record.image_id,
        status=record.status,
        stage=record.stage,
        progress=record.progress,
        message=record.message,
        error=record.error,
    )


def run_pipeline_job(job_id: str, request: JobRequest, storage: SessionStorage, registry: JobRegistry) -> None:
    try:
        image_path = storage.image_path(request.image_id)
        raw_mesh_path = storage.job_mesh_dir(request.image_id, job_id) / "raw_model.glb"
        cleaned_mesh_path = storage.job_mesh_dir(request.image_id, job_id) / "cleaned_model.glb"
        voxel_path = storage.job_voxel_dir(request.image_id, job_id) / "model_voxels.npz"
        ldr_path = storage.job_ldr_dir(request.image_id, job_id) / "output.ldr"
        report_path = storage.job_report_dir(request.image_id, job_id) / "report.json"
        mesh_inspect_path = storage.job_report_dir(request.image_id, job_id) / "mesh_inspect.json"
        registry.update(
            job_id,
            status="running",
            stage="reconstruction",
            progress=0.15,
            message="Generating fake SAM mesh",
            paths={
                "raw_mesh": raw_mesh_path,
                "cleaned_mesh": cleaned_mesh_path,
                "voxels": voxel_path,
                "ldr": ldr_path,
                "report": report_path,
                "mesh_inspect": mesh_inspect_path,
            },
        )
        registry.update(
            job_id,
            stage="mesh_inspection",
            progress=0.28,
            message="Generating and inspecting raw mesh before conversion",
        )
        run_from_image(
            image_path=image_path,
            runner=FakeSamMeshRunner(),
            raw_mesh_path=raw_mesh_path,
            cleaned_mesh_path=cleaned_mesh_path,
            voxel_output_path=voxel_path,
            ldr_output_path=ldr_path,
            target_longest_studs=request.target_studs,
            fill=request.fill,
            default_color_id=request.default_color_id,
            sample_colors=request.sample_colors,
            optimize=request.optimize,
            report_path=report_path,
            raw_mesh_report_path=mesh_inspect_path,
        )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        mesh_inspect = json.loads(mesh_inspect_path.read_text(encoding="utf-8"))
        warnings = list(mesh_inspect.get("warnings", []))
        result = JobResultResponse(
            job_id=job_id,
            status="completed",
            ldr_url=f"/api/jobs/{job_id}/files/ldr",
            report_url=f"/api/jobs/{job_id}/files/report",
            raw_mesh_url=f"/api/jobs/{job_id}/files/raw_mesh",
            cleaned_mesh_url=f"/api/jobs/{job_id}/files/cleaned_mesh",
            mesh_inspect_url=f"/api/jobs/{job_id}/files/mesh_inspect",
            voxel_url=f"/api/jobs/{job_id}/files/voxels",
            brick_count=report.get("output_brick_count"),
            reduction_percent=report.get("reduction_percent"),
            warnings=warnings,
        )
        registry.update(
            job_id,
            status="completed",
            stage="completed",
            progress=1.0,
            message="LDraw output and report generated",
            result=result,
        )
    except Exception as error:  # pragma: no cover - surfaced through API status.
        registry.update(
            job_id,
            status="failed",
            stage="failed",
            progress=1.0,
            message="Pipeline job failed",
            error=str(error),
        )
