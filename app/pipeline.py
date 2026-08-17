import json
from pathlib import Path

from . import ass_builder, burn, video_probe
from .caption_words import transcribe_words
from .config import settings

_SAMPLE_WORDS = [
    {"word": "sample", "start": 0.0, "end": 1.0},
    {"word": "caption", "start": 1.0, "end": 2.0},
    {"word": "text", "start": 2.0, "end": 3.0},
    {"word": "here", "start": 3.0, "end": 4.0},
]


def words_cache_path(job_dir: Path) -> Path:
    return job_dir / "words.json"


def thumbnail_path(job_dir: Path) -> Path:
    return job_dir / "thumbnail.jpg"


def load_cache(job_id: str) -> dict:
    job_dir = settings.data_dir / job_id
    cache_path = words_cache_path(job_dir)
    if not cache_path.exists():
        raise RuntimeError("No transcript for this job yet - generate one first")
    return json.loads(cache_path.read_text(encoding="utf-8"))


def save_words(job_id: str, words: list) -> None:
    job_dir = settings.data_dir / job_id
    cache_path = words_cache_path(job_dir)
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    cache["words"] = words
    cache_path.write_text(json.dumps(cache), encoding="utf-8")


def transcribe_pipeline(job_id: str, video_path_str: str, log, set_progress):
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

    words_cache_path(job_dir).write_text(
        json.dumps({"video_path": str(video_path), "width": width, "height": height, "duration": duration, "words": words}),
        encoding="utf-8",
    )

    set_progress("extracting_preview_frame")
    video_probe.extract_thumbnail(video_path, thumbnail_path(job_dir), duration)

    return {"word_count": len(words), "duration": duration}


def render_pipeline(
    job_id: str, log, set_progress,
    font_name: str | None = None, font_size: int | None = None, letter_spacing: float | None = None,
    words_per_group: int | None = None,
    pos_x_frac: float | None = None, pos_y_frac: float | None = None, all_caps: bool | None = None,
):
    job_dir = settings.data_dir / job_id
    cache = load_cache(job_id)
    video_path = Path(cache["video_path"])
    if not video_path.exists():
        raise FileNotFoundError(f"Source file no longer exists: {video_path}")

    font_name = font_name or "Arial"
    words_per_group = words_per_group or settings.words_per_group
    pos_x_frac = 0.5 if pos_x_frac is None else pos_x_frac
    pos_y_frac = 0.85 if pos_y_frac is None else pos_y_frac
    all_caps = settings.all_caps if all_caps is None else all_caps

    words = cache["words"]
    set_progress("building_captions")
    render_words = [{**w, "word": w["word"].upper()} for w in words] if all_caps else words
    ass_content = ass_builder.build_ass(
        render_words, cache["width"], cache["height"], words_per_group, settings.highlight_color, settings.text_color,
        font_name, pos_x_frac, pos_y_frac, font_size, letter_spacing or 0,
    )
    ass_path = job_dir / "captions.ass"
    ass_path.write_text(ass_content, encoding="utf-8")
    log(f"Wrote {ass_path.name} ({len(words)} words, groups of {words_per_group}, font {font_name}, caps={all_caps})")

    set_progress("burning_in")
    out_path = job_dir / f"{video_path.stem}_captioned.mp4"
    burn.burn_captions(video_path, ass_path, out_path, log)

    return {"output_path": str(out_path), "word_count": len(words), "duration": cache["duration"]}


def generate_style_preview(
    job_id: str,
    font_name: str | None = None, font_size: int | None = None, letter_spacing: float | None = None,
    words_per_group: int | None = None,
    pos_x_frac: float | None = None, pos_y_frac: float | None = None, all_caps: bool | None = None,
) -> bytes:
    job_dir = settings.data_dir / job_id
    frame_path = thumbnail_path(job_dir)
    if not frame_path.exists():
        raise RuntimeError("No preview frame for this job yet - generate a transcript first")

    cache = load_cache(job_id)
    words_per_group = words_per_group or settings.words_per_group
    sample = cache["words"][:words_per_group] if cache["words"] else _SAMPLE_WORDS[:words_per_group]
    offset = sample[0]["start"]
    sample = [{"word": w["word"], "start": w["start"] - offset, "end": w["end"] - offset} for w in sample]

    font_name = font_name or "Arial"
    pos_x_frac = 0.5 if pos_x_frac is None else pos_x_frac
    pos_y_frac = 0.85 if pos_y_frac is None else pos_y_frac
    all_caps = settings.all_caps if all_caps is None else all_caps
    render_sample = [{**w, "word": w["word"].upper()} for w in sample] if all_caps else sample

    ass_content = ass_builder.build_ass(
        render_sample, cache["width"], cache["height"], words_per_group, settings.highlight_color, settings.text_color,
        font_name, pos_x_frac, pos_y_frac, font_size, letter_spacing or 0,
    )
    ass_path = job_dir / "preview.ass"
    ass_path.write_text(ass_content, encoding="utf-8")

    return burn.burn_preview_frame(frame_path, ass_path)
