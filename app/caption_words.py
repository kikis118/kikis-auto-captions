import os
import sys
from pathlib import Path

from .config import settings

if sys.platform == "win32":
    _site_packages = Path(__file__).resolve().parent.parent / ".venv" / "Lib" / "site-packages" / "nvidia"
    for _dll_dir in (_site_packages / "cublas" / "bin", _site_packages / "cudnn" / "bin"):
        if _dll_dir.is_dir():
            os.add_dll_directory(str(_dll_dir))

_model = None
_device = None


def _build_model(device: str):
    compute_type = "float16" if device == "cuda" else "int8"
    from faster_whisper import WhisperModel
    return WhisperModel(settings.whisper_model, device=device, compute_type=compute_type)


def _get_model():
    global _model, _device
    if _model is None:
        _device = settings.whisper_device
        _model = _build_model(_device)
    return _model


def _run_transcribe(model, audio_path: Path, log):
    log("Running language detection + voice-activity pre-pass...")
    segments_iter, info = model.transcribe(str(audio_path), vad_filter=True, word_timestamps=True)
    words = []
    for seg in segments_iter:
        for w in (seg.words or []):
            word_text = w.word.strip()
            if word_text:
                words.append({"word": word_text, "start": w.start, "end": w.end})
    log(f"Detected language: {info.language}")
    return words


def transcribe_words(audio_path: Path, log):
    global _model, _device
    model = _get_model()
    try:
        words = _run_transcribe(model, audio_path, log)
    except RuntimeError as e:
        if _device != "cuda":
            raise
        log(f"GPU transcription failed ({e}); falling back to CPU (this will be slower)")
        _device = "cpu"
        _model = _build_model("cpu")
        words = _run_transcribe(_model, audio_path, log)
    log(f"Transcribed {len(words)} words")
    return words
