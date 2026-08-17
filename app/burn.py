import subprocess
from pathlib import Path

from .config import settings


def _ass_filter_arg(ass_path: Path) -> str:
    # ffmpeg's subtitles filter needs forward slashes and an escaped colon (drive letter) on Windows
    return str(ass_path).replace("\\", "/").replace(":", "\\:")


def burn_captions(video_path: Path, ass_path: Path, out_path: Path, log):
    args = [
        str(settings.ffmpeg_path), "-y",
        "-i", str(video_path),
        "-vf", f"subtitles='{_ass_filter_arg(ass_path)}'",
        "-c:a", "copy",
        str(out_path),
    ]
    log(f"$ {' '.join(args)}")
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        log(proc.stderr[-4000:])
        raise RuntimeError("ffmpeg burn-in failed")
    log("Burn-in complete")


def burn_preview_frame(frame_path: Path, ass_path: Path) -> bytes:
    """Burns the given .ass onto a single still image and returns JPEG bytes -
    same subtitles filter as the real burn, so it's WYSIWYG with the final output."""
    args = [
        str(settings.ffmpeg_path), "-y",
        "-loop", "1", "-i", str(frame_path),
        "-vf", f"subtitles='{_ass_filter_arg(ass_path)}'",
        "-frames:v", "1",
        "-f", "image2pipe", "-vcodec", "mjpeg", "-q:v", "3", "pipe:1",
    ]
    proc = subprocess.run(args, capture_output=True)
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(proc.stderr.decode(errors="replace")[-2000:])
    return proc.stdout
