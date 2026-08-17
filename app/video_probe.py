import re
import subprocess
from pathlib import Path

from .config import settings

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)")
_RES_RE = re.compile(r"Video:.*?(\d{2,5})x(\d{2,5})")


def probe(video_path: Path):
    proc = subprocess.run(
        [str(settings.ffmpeg_path), "-i", str(video_path)],
        capture_output=True, text=True,
    )
    out = proc.stderr

    duration = 0.0
    m = _DURATION_RE.search(out)
    if m:
        h, mi, s = m.groups()
        duration = int(h) * 3600 + int(mi) * 60 + float(s)

    width, height = 1080, 1920
    m = _RES_RE.search(out)
    if m:
        width, height = int(m.group(1)), int(m.group(2))

    return duration, width, height
