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
    # ASS \c override tag values (BGR hex, no alpha)
    highlight_color = os.getenv("HIGHLIGHT_COLOR", "&H00FFFF&")  # yellow
    text_color = os.getenv("TEXT_COLOR", "&HFFFFFF&")  # white


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
