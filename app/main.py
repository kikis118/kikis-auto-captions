import subprocess
import sys
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import pipeline
from .config import settings
from .jobs import create_job, get_elapsed_seconds, get_job, render_job, render_overlay_job

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


class JobRequest(BaseModel):
    video_path: str


class StyleSegment(BaseModel):
    start: float
    end: float
    highlight_color: str | None = None
    text_color: str | None = None
    outline_color: str | None = None


class RenderRequest(BaseModel):
    font_name: str | None = None
    font_size: int | None = None
    letter_spacing: float | None = None
    words_per_group: int | None = None
    pos_x_frac: float | None = None
    pos_y_frac: float | None = None
    all_caps: bool | None = None
    highlight_color: str | None = None
    text_color: str | None = None
    outline_color: str | None = None
    outline_width: int | None = None
    bold: bool | None = None
    style_segments: list[StyleSegment] | None = None
    chunk_mode: Literal["fixed", "dynamic"] = "fixed"
    min_words_per_group: int | None = None
    canvas_width: int | None = None
    canvas_height: int | None = None


class WordsRequest(BaseModel):
    words: list[dict]


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


@app.post("/api/jobs")
def api_create_job(req: JobRequest):
    job_id = create_job(req.video_path)
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}/words")
def api_get_words(job_id: str):
    try:
        cache = pipeline.load_cache(job_id)
    except RuntimeError as e:
        raise HTTPException(404, str(e))
    return {"words": cache["words"]}


@app.put("/api/jobs/{job_id}/words")
def api_save_words(job_id: str, req: WordsRequest):
    try:
        pipeline.save_words(job_id, req.words)
    except RuntimeError as e:
        raise HTTPException(404, str(e))
    return {"ok": True}


_CANVAS_FIELDS = {"canvas_width", "canvas_height"}


@app.post("/api/jobs/{job_id}/render")
def api_render_job(job_id: str, req: RenderRequest):
    # canvas_width/canvas_height only apply to the overlay export below - the burned-in
    # video always uses the source clip's real resolution, so they're excluded here.
    ok = render_job(job_id, **req.model_dump(exclude=_CANVAS_FIELDS))
    if not ok:
        raise HTTPException(400, "job not found, has no transcript yet, or is still running")
    return {"ok": True}


@app.post("/api/jobs/{job_id}/style-preview")
async def api_style_preview(job_id: str, req: RenderRequest):
    try:
        jpeg = await run_in_threadpool(
            pipeline.generate_style_preview, job_id, **req.model_dump(exclude=_CANVAS_FIELDS)
        )
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return Response(content=jpeg, media_type="image/jpeg")


@app.post("/api/jobs/{job_id}/export-overlay")
def api_export_overlay(job_id: str, req: RenderRequest):
    ok = render_overlay_job(job_id, **req.model_dump())
    if not ok:
        raise HTTPException(400, "job not found, has no transcript yet, or is still running")
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
        "overlay_status": job.get("overlay_status"),
        "overlay_result": job.get("overlay_result"),
        "overlay_error": job.get("overlay_error"),
        "elapsed_seconds": get_elapsed_seconds(job_id),
    }


app.mount("/output", StaticFiles(directory=settings.data_dir), name="output")
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
