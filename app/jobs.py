import threading
import time
import traceback
import uuid
from datetime import datetime, timezone

from .pipeline import render_pipeline, transcribe_pipeline

JOBS: dict[str, dict] = {}
_lock = threading.Lock()

HEARTBEAT_INTERVAL = 30
_RENDERABLE_STATES = ("transcript_ready", "done", "error")


def create_job(video_path: str) -> str:
    job_id = uuid.uuid4().hex[:12]
    now = time.monotonic()
    job = {
        "id": job_id,
        "video_path": video_path,
        "status": "queued",
        "log": [],
        "result": None,
        "error": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "_started_monotonic": now,
        "_last_log_monotonic": now,
    }
    with _lock:
        JOBS[job_id] = job
    threading.Thread(target=_run_transcribe, args=(job_id,), daemon=True).start()
    threading.Thread(target=_heartbeat, args=(job_id,), daemon=True).start()
    return job_id


def render_job(
    job_id: str, font_name: str | None = None, font_size: int | None = None, letter_spacing: float | None = None,
    words_per_group: int | None = None, pos_x_frac: float | None = None, pos_y_frac: float | None = None,
    all_caps: bool | None = None,
) -> bool:
    job = JOBS.get(job_id)
    if not job or job["status"] not in _RENDERABLE_STATES:
        return False
    job["status"] = "rendering"
    job["error"] = None
    job["_started_monotonic"] = time.monotonic()
    threading.Thread(
        target=_run_render,
        args=(job_id, font_name, font_size, letter_spacing, words_per_group, pos_x_frac, pos_y_frac, all_caps),
        daemon=True,
    ).start()
    threading.Thread(target=_heartbeat, args=(job_id,), daemon=True).start()
    return True


def _run_transcribe(job_id: str) -> None:
    job = JOBS[job_id]

    def log(msg: str):
        job["log"].append(msg)
        job["_last_log_monotonic"] = time.monotonic()

    def set_progress(status: str):
        job["status"] = status

    try:
        job["result"] = transcribe_pipeline(job_id, job["video_path"], log, set_progress)
        job["status"] = "transcript_ready"
    except Exception as e:
        job["error"] = str(e)
        job["status"] = "error"
        log(f"ERROR: {e}\n{traceback.format_exc()}")


def _run_render(job_id: str, font_name, font_size, letter_spacing, words_per_group, pos_x_frac, pos_y_frac, all_caps) -> None:
    job = JOBS[job_id]

    def log(msg: str):
        job["log"].append(msg)
        job["_last_log_monotonic"] = time.monotonic()

    def set_progress(status: str):
        job["status"] = status

    try:
        job["result"] = render_pipeline(
            job_id, log, set_progress, font_name, font_size, letter_spacing, words_per_group,
            pos_x_frac, pos_y_frac, all_caps,
        )
        job["status"] = "done"
    except Exception as e:
        job["error"] = str(e)
        job["status"] = "error"
        log(f"ERROR: {e}\n{traceback.format_exc()}")


def _heartbeat(job_id: str) -> None:
    job = JOBS[job_id]
    while True:
        time.sleep(HEARTBEAT_INTERVAL)
        if job["status"] in ("transcript_ready", "done", "error"):
            return
        now = time.monotonic()
        elapsed = int(now - job["_started_monotonic"])
        since_log = int(now - job["_last_log_monotonic"])
        job["log"].append(
            f"[heartbeat] still running - {elapsed}s total elapsed, "
            f"{since_log}s since last log line - status: {job['status']}"
        )


def get_job(job_id: str):
    return JOBS.get(job_id)


def get_elapsed_seconds(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        return None
    return time.monotonic() - job["_started_monotonic"]
