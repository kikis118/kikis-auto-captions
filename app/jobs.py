import threading
import time
import traceback
import uuid
from datetime import datetime, timezone

from .pipeline import rerender_pipeline, run_pipeline

JOBS: dict[str, dict] = {}
_lock = threading.Lock()

HEARTBEAT_INTERVAL = 30


def create_job(
    video_path: str, font_name: str | None = None, words_per_group: int | None = None,
    pos_x_frac: float | None = None, pos_y_frac: float | None = None, all_caps: bool | None = None,
) -> str:
    job_id = uuid.uuid4().hex[:12]
    now = time.monotonic()
    job = {
        "id": job_id,
        "video_path": video_path,
        "font_name": font_name,
        "words_per_group": words_per_group,
        "pos_x_frac": pos_x_frac,
        "pos_y_frac": pos_y_frac,
        "all_caps": all_caps,
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
    threading.Thread(target=_run, args=(job_id,), daemon=True).start()
    threading.Thread(target=_heartbeat, args=(job_id,), daemon=True).start()
    return job_id


def rerender_job(
    job_id: str, font_name: str | None = None, words_per_group: int | None = None,
    pos_x_frac: float | None = None, pos_y_frac: float | None = None, all_caps: bool | None = None,
) -> bool:
    job = JOBS.get(job_id)
    if not job or job["status"] not in ("done", "error"):
        return False
    job["status"] = "rendering"
    job["error"] = None
    threading.Thread(
        target=_rerun, args=(job_id, font_name, words_per_group, pos_x_frac, pos_y_frac, all_caps), daemon=True
    ).start()
    return True


def _run(job_id: str) -> None:
    job = JOBS[job_id]

    def log(msg: str):
        job["log"].append(msg)
        job["_last_log_monotonic"] = time.monotonic()

    def set_progress(status: str):
        job["status"] = status

    try:
        job["result"] = run_pipeline(
            job_id, job["video_path"], log, set_progress,
            job["font_name"], job["words_per_group"], job["pos_x_frac"], job["pos_y_frac"], job["all_caps"],
        )
        job["status"] = "done"
    except Exception as e:
        job["error"] = str(e)
        job["status"] = "error"
        log(f"ERROR: {e}\n{traceback.format_exc()}")


def _rerun(job_id: str, font_name, words_per_group, pos_x_frac, pos_y_frac, all_caps) -> None:
    job = JOBS[job_id]

    def log(msg: str):
        job["log"].append(msg)
        job["_last_log_monotonic"] = time.monotonic()

    def set_progress(status: str):
        job["status"] = status

    try:
        job["result"] = rerender_pipeline(
            job_id, log, set_progress, font_name, words_per_group, pos_x_frac, pos_y_frac, all_caps,
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
        if job["status"] in ("done", "error"):
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
