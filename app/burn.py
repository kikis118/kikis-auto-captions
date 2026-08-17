import subprocess
from pathlib import Path

from .config import settings


def burn_captions(video_path: Path, ass_path: Path, out_path: Path, log):
    # ffmpeg's subtitles filter needs forward slashes and an escaped colon (drive letter) on Windows
    ass_arg = str(ass_path).replace("\\", "/").replace(":", "\\:")
    args = [
        str(settings.ffmpeg_path), "-y",
        "-i", str(video_path),
        "-vf", f"subtitles='{ass_arg}'",
        "-c:a", "copy",
        str(out_path),
    ]
    log(f"$ {' '.join(args)}")
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        log(proc.stderr[-4000:])
        raise RuntimeError("ffmpeg burn-in failed")
    log("Burn-in complete")
