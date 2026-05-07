from __future__ import annotations

from io import BytesIO
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from makeyourbrick.server.main import create_app
from makeyourbrick.server.storage import SessionStorage


def make_png_bytes(size: tuple[int, int] = (32, 24)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (242, 205, 55)).save(buffer, format="PNG")
    return buffer.getvalue()


def make_client() -> TestClient:
    storage = SessionStorage(Path("outputs/test_ui_sessions"))
    return TestClient(create_app(storage))


def test_health_endpoint_returns_ok() -> None:
    client = make_client()

    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_config_endpoint_returns_runner_settings() -> None:
    client = make_client()

    response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["runner_mode"] == "fake"
    assert payload["has_sam_command"] is False
    assert payload["requires_mask"] is False


def test_upload_image_stores_file_and_returns_metadata() -> None:
    client = make_client()

    response = client.post(
        "/api/images",
        files={"file": ("sample.png", make_png_bytes(), "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["image_id"]
    assert payload["image_url"].endswith("/file")
    assert payload["width"] == 32
    assert payload["height"] == 24

    file_response = client.get(payload["image_url"])
    assert file_response.status_code == 200
    assert file_response.content.startswith(b"\x89PNG")


def test_selection_endpoint_writes_placeholder_mask() -> None:
    client = make_client()
    upload = client.post(
        "/api/images",
        files={"file": ("sample.png", make_png_bytes(), "image/png")},
    ).json()

    response = client.post(
        f"/api/images/{upload['image_id']}/selection",
        json={
            "positive_points": [[10, 10]],
            "negative_points": [[20, 10]],
            "box": [4, 4, 28, 20],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["mask_id"]

    mask_response = client.get(payload["mask_url"])
    assert mask_response.status_code == 200
    assert mask_response.content.startswith(b"\x89PNG")


def test_upload_rejects_unsupported_extension() -> None:
    client = make_client()

    response = client.post(
        "/api/images",
        files={"file": ("sample.txt", b"not an image", "text/plain")},
    )

    assert response.status_code == 400
