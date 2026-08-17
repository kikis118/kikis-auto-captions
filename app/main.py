import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import settings
from .jobs import create_job, get_elapsed_seconds, get_job

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


def _run_native_picker() -> str:
    result = subprocess.run(
        [sys.executable, "-c", _PICKER_SCRIPT], capture_output=True, text=True
    )
    return result.stdout.strip()


class JobRequest(BaseModel):
    video_path: str


@app.post("/api/browse-native")
async def api_browse_native():
    path = await run_in_threadpool(_run_native_picker)
    return {"path": path}


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
