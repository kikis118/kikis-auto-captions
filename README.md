# Kikis Auto Captions

Burns in word-by-word highlighted captions onto a video clip — the rolling "3-4 words on screen, one highlighted as it's spoken" TikTok/CapCut style — running entirely on your own PC.

## What this does

- You give it a video file.
- It listens to the audio and figures out every word and exactly when it's spoken.
- It burns in captions where each word lights up as it's said, in the font, size, position, and casing you choose.
- Everything runs on your computer. No accounts, no API keys, no subscriptions, and no internet needed once it's set up.

## What you need before starting

1. **Windows** — this tool is built for Windows only.
2. **Python 3.11 or newer.** Download it from [python.org/downloads](https://www.python.org/downloads/) — get the latest 3.11+ Windows installer. On the first setup screen, tick **"Add python.exe to PATH"** before clicking install.
3. **ffmpeg** — a free tool this app uses to read and write video. Get it from [ffmpeg.org/download.html](https://ffmpeg.org/download.html): click the Windows icon and pick any of the linked Windows builds. It downloads as a `.zip` — extract it anywhere (e.g. `C:\ffmpeg`) and note the full path to `ffmpeg.exe` inside its `bin` folder (e.g. `C:\ffmpeg\bin\ffmpeg.exe`). You'll need that path in Setup below.
4. **An NVIDIA graphics card is strongly recommended, but not required.** Without one, the tool automatically falls back to your CPU — it still works, just much slower (a several-minute clip can take a good while on CPU vs. close to real-time on an NVIDIA GPU).
5. **A few GB of free disk space** — the first time you run a job, it downloads a speech-recognition model that then gets reused for every job after that.

No Gemini, no Claude, no API keys, no billing, no account of any kind — everything here runs locally.

## Get the code

If you're reading this on GitHub: click the green **Code** button near the top of the repo page → **Download ZIP** → extract it anywhere on your PC (e.g. your Desktop). That folder is what the rest of these instructions call "this folder."

(If you're comfortable with git instead: `git clone` the repo URL and use that folder.)

## One-time setup

Open a terminal (PowerShell or Command Prompt) in this folder, then run:

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

Then open the new `.env` file in Notepad and set `FFMPEG_PATH` to wherever you extracted ffmpeg, for example:

```
FFMPEG_PATH=C:\ffmpeg\bin\ffmpeg.exe
```

That's the only setting you need to change. Everything else in `.env` is optional and already has a working default.

## Running it

Double-click **`start.bat`** in this folder. That's it — it starts the app and opens it in your browser at `http://localhost:8001`.

(You only need the manual command below if `start.bat` doesn't work for some reason: `.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001`, then open `http://localhost:8001` yourself.)

## Using it

1. **Choose your clip** — click **Browse...** to open the normal Windows file picker and select your video.
2. **Generate transcript** — click it and wait; it listens to the clip and writes down every word with its timing. This is the one step that takes real time (longer without an NVIDIA GPU).
3. **Review the transcript** — every word appears editable. Click any word Whisper misheard and fix it — it saves automatically.
4. **Style your captions** — pick a font, size, letter spacing, how many words show on screen, ALL CAPS on/off, and drag the caption to where you want it. The preview here is rendered by the exact same engine as the final video, so it's not an approximation — what you see is what you'll get.
5. **Burn captions in** — click it. The finished video plays right there when it's done, with its file location shown underneath.

Not quite right? Change anything in step 3 or 4 and click **Re-render with new style** — it reuses the transcript, so it's fast and doesn't re-listen to the clip.

Everything stays on your PC — no files, audio, or text are ever sent anywhere. The finished video (and a working folder for that job) is saved under `data/<job-id>/`.

## How it works (for developers)

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, HTTP endpoints |
| `app/jobs.py` | In-memory job tracking; separate background-thread paths for transcription vs. render, each with a 30s heartbeat |
| `app/pipeline.py` | `transcribe_pipeline` (probe → transcribe → cache `words.json` → extract a preview frame) and `render_pipeline` (load cached words → build captions → burn in) are separate stages, so restyling never re-transcribes. `generate_style_preview` builds a tiny sample `.ass` from the real cached transcript and burns it onto the cached preview frame — the exact same code path as the real burn, just on one still image |
| `app/video_probe.py` | Reads resolution/duration via `ffmpeg -i`; extracts a representative still frame for previews |
| `app/caption_words.py` | `faster-whisper` with `word_timestamps=True` — GPU by default with automatic CPU fallback (CUDA DLLs come from the `nvidia-cublas-cu12`/`nvidia-cudnn-cu12` pip packages, no system CUDA install needed) |
| `app/ass_builder.py` | Builds an `.ass` subtitle file: words chunked into rolling groups, one `Dialogue` line per word with an inline color-override tag marking the currently-spoken word, positioned via an explicit `\pos()` tag, with font size and letter spacing as Style-level overrides |
| `app/burn.py` | `burn_captions` hard-burns the `.ass` onto the full source video; `burn_preview_frame` does the same onto a single still image, for the style preview |
| `app/config.py` | Settings, overridable via `.env` |
| `app/utils.py` | Time formatting helper |

Each job's working files (probed video info, cached transcript, preview frame, generated `.ass`, final captioned `.mp4`) live under `data/<job_id>/`.
