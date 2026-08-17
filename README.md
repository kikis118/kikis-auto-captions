# Kikis Auto Captions

Takes a finished, exported video clip and burns in word-by-word highlighted captions — the rolling "3-4 words on screen, one highlighted as it's spoken" TikTok/CapCut style — without CapCut, without a Pro subscription, and without the screen-record-the-preview workaround.

**Why re-transcribe the clip itself** (instead of tracking timestamps back from a longer VOD transcript, e.g. from [Kikis Shorts Tool](../Kikis_Shorts_Tool)): once a clip has been cut, trimmed, or reordered in an editor, mapping "this point in the final video" back to "this point in the original VOD" is a genuinely hard alignment problem. Re-transcribing the actual exported file sidesteps that entirely — the captions are guaranteed to match whatever is actually in the final cut, including any edits.

## Requirements

- Windows
- Python 3.11+
- An NVIDIA GPU is strongly recommended (falls back to CPU automatically, much slower)
- `ffmpeg` (a path is required — see Setup)

No API keys needed — everything runs locally.

## Setup

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

`.env` is optional — every setting has a working default. See `.env.example` for what's overridable (ffmpeg path, Whisper model/device, caption styling).

## Running

- Double-click the **Kikis Auto Captions** desktop shortcut (runs `start.bat`), or
- Manually: `.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir . --host 127.0.0.1 --port 8001`

Opens at `http://localhost:8001`.

## Using it

1. Export your finished cut from your editor (video, typically without music yet).
2. Paste the full local file path into the tool.
3. Click **Run** — it transcribes the clip (word-level timestamps), builds the caption styling, and burns it into a new video file.
4. Once done, preview it inline and find the output path (saved next to a per-job folder under `data/`) — bring that back into your editor to add music/final touches.

## Caption styling

Defaults: rolling groups of 4 words, current word highlighted yellow, rest white, positioned in the lower third. All tunable via `.env` — see `WORDS_PER_GROUP`, `HIGHLIGHT_COLOR`, `TEXT_COLOR` in `.env.example`. Colors are ASS-subtitle `\c` override values (`&HBBGGRR&` hex, no alpha).

## How it works (for developers)

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, HTTP endpoints |
| `app/jobs.py` | In-memory job tracking, background thread + 30s heartbeat (same pattern as Kikis Shorts Tool) |
| `app/pipeline.py` | Orchestrates one run: probe → transcribe → build captions → burn in |
| `app/video_probe.py` | Reads the source video's resolution/duration via `ffmpeg -i` |
| `app/caption_words.py` | `faster-whisper` with `word_timestamps=True` — GPU by default with automatic CPU fallback (same CUDA DLL wiring as Kikis Shorts Tool, see that project's README for why) |
| `app/ass_builder.py` | Builds an `.ass` subtitle file: words chunked into rolling groups, one `Dialogue` line per word with an inline color-override tag marking the currently-spoken word |
| `app/burn.py` | Runs `ffmpeg`'s `subtitles` filter to hard-burn the `.ass` onto the source video |
| `app/config.py` | Settings, overridable via `.env` |
| `app/utils.py` | Time formatting helper |

Each job's working files (probed video info, the generated `.ass`, the final captioned `.mp4`) live under `data/<job_id>/`.
