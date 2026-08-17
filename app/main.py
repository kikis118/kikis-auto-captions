import os
import string
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .jobs import create_job, get_elapsed_seconds, get_job

app = FastAPI(title="Kikis Auto Captions")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v", ".flv", ".wmv"}


class JobRequest(BaseModel):
    video_path: str


def _list_drives() -> list[str]:
    if os.name != "nt":
        return ["/"]
    return [f"{letter}:\\" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]


@app.get("/api/browse")
def api_browse(path: str = ""):
    if not path:
        return {"path": "", "parent": None, "dirs": _list_drives(), "files": []}

    p = Path(path)
    if not p.exists() or not p.is_dir():
        raise HTTPException(400, "not a valid directory")

    try:
        entries = list(p.iterdir())
    except PermissionError:
        raise HTTPException(403, "permission denied")

    dirs = sorted((e.name for e in entries if e.is_dir() and not e.name.startswith(".")), key=str.lower)
    files = sorted(
        (e.name for e in entries if e.is_file() and e.suffix.lower() in VIDEO_EXTENSIONS),
        key=str.lower,
    )
    parent = None if p.parent == p else str(p.parent)
    return {"path": str(p), "parent": parent, "dirs": dirs, "files": files}


@app.post("/api/jobs")
def api_create_job(req: JobRequest):
    job_id = create_job(req.video_path)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def api_get_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "id": job["id"],
        "status": job["status"],
        "log": job["log"][-200:],
        "result": job["result"],
        "error": job["error"],
        "elapsed_seconds": get_elapsed_seconds(job_id),
    }


app.mount("/output", StaticFiles(directory=settings.data_dir), name="output")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
