import json
from pathlib import Path

from . import ass_builder, burn, video_probe
from .caption_words import transcribe_words
from .config import settings


def _words_cache_path(job_dir: Path) -> Path:
    return job_dir / "words.json"


def render_captions(
    job_id: str, job_dir: Path, video_path: Path, words: list, width: int, height: int, duration: float,
    log, set_progress,
    font_name: str | None = None, words_per_group: int | None = None,
    pos_x_frac: float | None = None, pos_y_frac: float | None = None, all_caps: bool | None = None,
):
    font_name = font_name or "Arial"
    words_per_group = words_per_group or settings.words_per_group
    pos_x_frac = 0.5 if pos_x_frac is None else pos_x_frac
    pos_y_frac = 0.85 if pos_y_frac is None else pos_y_frac
    all_caps = settings.all_caps if all_caps is None else all_caps

    set_progress("building_captions")
    render_words = [{**w, "word": w["word"].upper()} for w in words] if all_caps else words
    ass_content = ass_builder.build_ass(
        render_words, width, height, words_per_group, settings.highlight_color, settings.text_color,
        font_name, pos_x_frac, pos_y_frac,
    )
    ass_path = job_dir / "captions.ass"
    ass_path.write_text(ass_content, encoding="utf-8")
    log(f"Wrote {ass_path.name} ({len(words)} words, groups of {words_per_group}, font {font_name}, caps={all_caps})")

    set_progress("burning_in")
    out_path = job_dir / f"{video_path.stem}_captioned.mp4"
    burn.burn_captions(video_path, ass_path, out_path, log)

    return {"output_path": str(out_path), "word_count": len(words), "duration": duration}


def run_pipeline(
    job_id: str, video_path_str: str, log, set_progress,
    font_name: str | None = None, words_per_group: int | None = None,
    pos_x_frac: float | None = None, pos_y_frac: float | None = None, all_caps: bool | None = None,
):
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

    _words_cache_path(job_dir).write_text(
        json.dumps({"video_path": str(video_path), "width": width, "height": height, "duration": duration, "words": words}),
        encoding="utf-8",
    )

    return render_captions(
        job_id, job_dir, video_path, words, width, height, duration, log, set_progress,
        font_name, words_per_group, pos_x_frac, pos_y_frac, all_caps,
    )


def rerender_pipeline(
    job_id: str, log, set_progress,
    font_name: str | None = None, words_per_group: int | None = None,
    pos_x_frac: float | None = None, pos_y_frac: float | None = None, all_caps: bool | None = None,
):
    job_dir = settings.data_dir / job_id
    cache_path = _words_cache_path(job_dir)
    if not cache_path.exists():
        raise RuntimeError("No cached transcript for this job - run it fresh first")

    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    video_path = Path(cache["video_path"])
    if not video_path.exists():
        raise FileNotFoundError(f"Source file no longer exists: {video_path}")

    log("Re-rendering captions with the updated style (reusing cached transcript, no re-transcription needed)")
    return render_captions(
        job_id, job_dir, video_path, cache["words"], cache["width"], cache["height"], cache["duration"],
        log, set_progress, font_name, words_per_group, pos_x_frac, pos_y_frac, all_caps,
    )
