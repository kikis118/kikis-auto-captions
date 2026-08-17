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

- Double-click the **Kikis Auto Captions** desktop shortcut (if one was set up for you), or
- Open a terminal in this folder and run:
  ```bash
  .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
  ```
  then open `http://localhost:8001` in your browser.

## Using it

1. **Choose your clip** — click **Browse...** to open the normal Windows file picker and select your video.
2. **Style your captions** — a live preview of a real frame from your video appears. Pick a font, choose how many words show on screen at once, toggle **ALL CAPS** on or off, and drag the sample caption to wherever you want it to sit. Everything updates live before you commit to anything.
3. **Run** — once it looks right, click **Run**. It transcribes the audio and burns the captions in, with progress shown in the log.
4. **Check the result** — the finished video plays right there, with its file location shown underneath.
5. **Not quite right?** Change the font, caps, word count, or drag the position again, then click **Re-render with new style**. This reuses the transcript from the run you just did, so it's fast — it doesn't need to re-listen to the whole clip.

Everything stays on your PC — no files, audio, or text are ever sent anywhere. The finished video (and a working folder for that job) is saved under `data/<job-id>/`.

## How it works (for developers)

| File | Responsibility |
|---|---|
| `app/main.py` | FastAPI app, HTTP endpoints |
| `app/jobs.py` | In-memory job tracking; background thread per run + 30s heartbeat; also handles fast "re-render" jobs that reuse a cached transcript |
| `app/pipeline.py` | Orchestrates a fresh run: probe → transcribe → cache transcript to `words.json` → build captions → burn in. Re-render skips straight to build → burn using that cached transcript |
| `app/video_probe.py` | Reads the source video's resolution/duration via `ffmpeg -i` |
| `app/caption_words.py` | `faster-whisper` with `word_timestamps=True` — GPU by default with automatic CPU fallback (CUDA DLLs come from the `nvidia-cublas-cu12`/`nvidia-cudnn-cu12` pip packages, no system CUDA install needed) |
| `app/ass_builder.py` | Builds an `.ass` subtitle file: words chunked into rolling groups, one `Dialogue` line per word with an inline color-override tag marking the currently-spoken word, positioned via an explicit `\pos()` tag |
| `app/burn.py` | Runs ffmpeg's `subtitles` filter to hard-burn the `.ass` onto the source video |
| `app/config.py` | Settings, overridable via `.env` |
| `app/utils.py` | Time formatting helper |

Each job's working files (probed video info, cached transcript, generated `.ass`, final captioned `.mp4`) live under `data/<job_id>/`.
