import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import video_probe
from .config import settings
from .jobs import create_job, get_elapsed_seconds, get_job, rerender_job

app = FastAPI(title="Kikis Auto Captions")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

_PICKER_SCRIPT = """
import tkinter
from tkinter import filedialog
root = tkinter.Tk()
root.withdraw()
root.attributes("-topmost", True)
path = filedialog.askopenfilename(
    title="Select clip to caption",
    filetypes=[
        ("Video files", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v *.flv *.wmv"),
        ("All files", "*.*"),
    ],
)
print(path)
"""

_FONTS_SCRIPT = """
import tkinter
from tkinter import font
root = tkinter.Tk()
root.withdraw()
for name in sorted(set(font.families())):
    if not name.startswith("@"):
        print(name)
"""

_fonts_cache: list[str] | None = None


def _run_native_picker() -> str:
    result = subprocess.run(
        [sys.executable, "-c", _PICKER_SCRIPT], capture_output=True, text=True
    )
    return result.stdout.strip()


def _list_fonts() -> list[str]:
    result = subprocess.run(
        [sys.executable, "-c", _FONTS_SCRIPT], capture_output=True, text=True
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _resolve_video_path(raw: str) -> Path:
    p = Path(raw.strip().strip('"'))
    if not p.exists() or not p.is_file():
        raise HTTPException(404, "file not found")
    return p


class JobRequest(BaseModel):
    video_path: str
    font_name: str | None = None
    words_per_group: int | None = None
    pos_x_frac: float | None = None
    pos_y_frac: float | None = None
    all_caps: bool | None = None


class RerenderRequest(BaseModel):
    font_name: str | None = None
    words_per_group: int | None = None
    pos_x_frac: float | None = None
    pos_y_frac: float | None = None
    all_caps: bool | None = None


@app.post("/api/browse-native")
async def api_browse_native():
    path = await run_in_threadpool(_run_native_picker)
    return {"path": path}


@app.get("/api/fonts")
async def api_fonts():
    global _fonts_cache
    if _fonts_cache is None:
        _fonts_cache = await run_in_threadpool(_list_fonts)
    return {"fonts": _fonts_cache}


@app.get("/api/thumbnail")
def api_thumbnail(video_path: str):
    p = _resolve_video_path(video_path)
    duration, _, _ = video_probe.probe(p)
    args = [
        str(settings.ffmpeg_path), "-ss", str(duration / 2 if duration else 0), "-i", str(p),
        "-frames:v", "1", "-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "3", "pipe:1",
    ]
    proc = subprocess.run(args, capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        raise HTTPException(500, "failed to extract thumbnail")
    return Response(content=proc.stdout, media_type="image/jpeg")


@app.post("/api/jobs")
def api_create_job(req: JobRequest):
    job_id = create_job(
        req.video_path, req.font_name, req.words_per_group, req.pos_x_frac, req.pos_y_frac, req.all_caps
    )
    return {"job_id": job_id}


@app.post("/api/jobs/{job_id}/rerender")
def api_rerender_job(job_id: str, req: RerenderRequest):
    ok = rerender_job(job_id, req.font_name, req.words_per_group, req.pos_x_frac, req.pos_y_frac, req.all_caps)
    if not ok:
        raise HTTPException(400, "job not found, or still running")
    return {"ok": True}


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
