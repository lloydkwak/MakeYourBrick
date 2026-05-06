from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

from PIL import Image
from fastapi import UploadFile

from makeyourbrick.server.schemas import SelectionRequest


ALLOWED_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


class SessionStorage:
    def __init__(self, root: Path = Path("outputs/ui_sessions")) -> None:
        self.root = root

    def new_id(self) -> str:
        return uuid4().hex

    def session_dir(self, image_id: str) -> Path:
        return self.root / image_id

    def input_dir(self, image_id: str) -> Path:
        return self.session_dir(image_id) / "input"

    def selection_dir(self, image_id: str) -> Path:
        return self.session_dir(image_id) / "selection"

    def job_dir(self, image_id: str, job_id: str) -> Path:
        return self.session_dir(image_id) / "jobs" / job_id

    def job_mesh_dir(self, image_id: str, job_id: str) -> Path:
        return self.job_dir(image_id, job_id) / "meshes"

    def job_voxel_dir(self, image_id: str, job_id: str) -> Path:
        return self.job_dir(image_id, job_id) / "voxels"

    def job_ldr_dir(self, image_id: str, job_id: str) -> Path:
        return self.job_dir(image_id, job_id) / "ldr"

    def job_report_dir(self, image_id: str, job_id: str) -> Path:
        return self.job_dir(image_id, job_id) / "reports"

    def image_path(self, image_id: str) -> Path:
        matches = list(self.input_dir(image_id).glob("image.*"))
        if not matches:
            raise FileNotFoundError(f"Image not found for id: {image_id}")
        return matches[0]

    def mask_path(self, image_id: str, mask_id: str) -> Path:
        return self.selection_dir(image_id) / f"{mask_id}.png"

    async def save_upload(self, upload: UploadFile) -> tuple[str, Path, Image.Image]:
        suffix = Path(upload.filename or "").suffix.lower()
        if suffix not in ALLOWED_IMAGE_SUFFIXES:
            raise ValueError(f"Unsupported image type: {suffix or 'unknown'}")
        image_id = self.new_id()
        directory = self.input_dir(image_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"image{suffix}"
        with path.open("wb") as file:
            shutil.copyfileobj(upload.file, file)
        image = Image.open(path)
        image.load()
        return image_id, path, image

    def save_selection(self, image_id: str, mask_id: str, selection: SelectionRequest) -> Path:
        directory = self.selection_dir(image_id)
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{mask_id}.json"
        path.write_text(selection.model_dump_json(indent=2), encoding="utf-8")
        return path

    def read_manifest(self, image_id: str) -> dict:
        manifest_path = self.session_dir(image_id) / "manifest.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest not found for id: {image_id}")
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def write_manifest(self, image_id: str, data: dict) -> Path:
        path = self.session_dir(image_id) / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path
