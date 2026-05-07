from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

from makeyourbrick.server.jobs import JobRunnerConfig
from makeyourbrick.server.main import create_app
from makeyourbrick.server.storage import SessionStorage
from tests.test_server_api import make_png_bytes


def make_client(runner_config: JobRunnerConfig | None = None) -> TestClient:
    storage = SessionStorage(Path("outputs/test_ui_job_sessions"))
    return TestClient(create_app(storage, runner_config=runner_config))


def test_job_stub_generates_ldr_report_and_artifact_links() -> None:
    client = make_client()
    upload = client.post(
        "/api/images",
        files={"file": ("sample.png", make_png_bytes(), "image/png")},
    ).json()
    selection = client.post(
        f"/api/images/{upload['image_id']}/selection",
        json={
            "positive_points": [[12, 10]],
            "negative_points": [],
            "box": [4, 4, 28, 20],
        },
    ).json()

    response = client.post(
        "/api/jobs",
        json={
            "image_id": upload["image_id"],
            "mask_id": selection["mask_id"],
            "target_studs": 8,
            "sample_colors": True,
            "optimize": True,
            "fill": True,
            "default_color_id": 16,
            "repair_mode": "basic",
        },
    )

    assert response.status_code == 200
    job = response.json()
    assert job["job_id"]

    status = client.get(f"/api/jobs/{job['job_id']}").json()
    assert status["status"] == "completed"
    assert status["progress"] == 1.0

    result_response = client.get(f"/api/jobs/{job['job_id']}/result")
    assert result_response.status_code == 200
    result = result_response.json()
    assert result["brick_count"] > 0
    assert result["reduction_percent"] >= 0
    assert result["mesh_inspect_url"].endswith("/files/mesh_inspect")
    assert result["repair_report_url"].endswith("/files/repair_report")

    ldr_response = client.get(result["ldr_url"])
    assert ldr_response.status_code == 200
    assert "3005.dat" in ldr_response.text or "3001.dat" in ldr_response.text

    mesh_inspect_response = client.get(result["mesh_inspect_url"])
    assert mesh_inspect_response.status_code == 200
    assert mesh_inspect_response.json()["voxelization_ready"] is True

    repair_report_response = client.get(result["repair_report_url"])
    assert repair_report_response.status_code == 200
    assert repair_report_response.json()["mode_requested"] == "basic"

    report_response = client.get(result["report_url"])
    assert report_response.status_code == 200
    assert report_response.json()["output_brick_count"] == result["brick_count"]


def test_job_stub_rejects_missing_image() -> None:
    client = make_client()

    response = client.post("/api/jobs", json={"image_id": "missing"})

    assert response.status_code == 404


def test_job_can_use_command_runner_config() -> None:
    client = make_client(
        JobRunnerConfig(
            mode="command",
            sam_repo=Path("."),
            sam_command=f"{sys.executable} tests/fake_sam3d_command.py --colored-box --output {{output}}",
            timeout_seconds=10,
        )
    )
    upload = client.post(
        "/api/images",
        files={"file": ("sample.png", make_png_bytes(), "image/png")},
    ).json()

    response = client.post(
        "/api/jobs",
        json={
            "image_id": upload["image_id"],
            "target_studs": 8,
            "sample_colors": True,
            "optimize": False,
            "fill": True,
            "default_color_id": 16,
            "repair_mode": "basic",
        },
    )

    assert response.status_code == 200
    job = response.json()
    status = client.get(f"/api/jobs/{job['job_id']}").json()
    assert status["status"] == "completed"
    assert status["message"] == "LDraw output and report generated"

    result = client.get(f"/api/jobs/{job['job_id']}/result").json()
    assert result["brick_count"] > 0
