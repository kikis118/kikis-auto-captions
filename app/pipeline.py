from pathlib import Path

from . import ass_builder, burn, video_probe
from .caption_words import transcribe_words
from .config import settings


def run_pipeline(job_id: str, video_path_str: str, log, set_progress):
    video_path = Path(video_path_str.strip().strip('"'))
    if not video_path.exists():
        raise FileNotFoundError(f"File not found: {video_path}")

    job_dir = settings.data_dir / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    set_progress("probing")
    duration, width, height = video_probe.probe(video_path)
    log(f"Video: {width}x{height}, {duration:.1f}s")

    set_progress("transcribing")
    words = transcribe_words(video_path, log)
    if not words:
        raise RuntimeError("No words transcribed - is there audio in this file?")

    set_progress("building_captions")
    ass_content = ass_builder.build_ass(
        words, width, height, settings.words_per_group, settings.highlight_color, settings.text_color
    )
    ass_path = job_dir / "captions.ass"
    ass_path.write_text(ass_content, encoding="utf-8")
    log(f"Wrote {ass_path.name} ({len(words)} words, groups of {settings.words_per_group})")

    set_progress("burning_in")
    out_path = job_dir / f"{video_path.stem}_captioned.mp4"
    burn.burn_captions(video_path, ass_path, out_path, log)

    return {"output_path": str(out_path), "word_count": len(words), "duration": duration}
