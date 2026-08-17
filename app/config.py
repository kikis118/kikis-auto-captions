import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

APP_DIR = Path(__file__).resolve().parent.parent


class Settings:
    ffmpeg_path = Path(os.getenv(
        "FFMPEG_PATH",
        r"C:\Users\krist\Desktop\TwitchDownloader\ffmpeg.exe",
    ))
    data_dir = Path(os.getenv("DATA_DIR", APP_DIR / "data"))

    whisper_model = os.getenv("WHISPER_MODEL", "large-v3")
    whisper_device = os.getenv("WHISPER_DEVICE", "cuda")

    words_per_group = int(os.getenv("WORDS_PER_GROUP", "4"))
    all_caps = os.getenv("ALL_CAPS", "true").lower() in ("1", "true", "yes")
    # a speech pause longer than this (seconds) starts a new caption group early,
    # so words don't appear on screen before they're actually said
    max_group_gap = float(os.getenv("MAX_GROUP_GAP", "0.5"))
    # ASS \c override tag values (BGR hex, no alpha)
    highlight_color = os.getenv("HIGHLIGHT_COLOR", "&H00FFFF&")  # yellow
    text_color = os.getenv("TEXT_COLOR", "&HFFFFFF&")  # white
    # ASS Style-line color field (opaque AABBGGRR)
    outline_color = os.getenv("OUTLINE_COLOR", "&H00000000")  # black
    outline_width = int(os.getenv("OUTLINE_WIDTH", "4"))
    bold = os.getenv("BOLD", "true").lower() in ("1", "true", "yes")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
