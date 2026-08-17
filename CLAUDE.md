# Kikis Auto Captions — notes for future Claude sessions

See `README.md` for user/developer docs. This file is operational context that isn't obvious from reading the code cold.

## Running it during development

- Static files are served fresh — no restart needed after editing them.
- Backend `.py` changes need a server restart (uvicorn isn't running with `--reload`).
- Launch config lives in the parent project's `.claude/launch.json` (`kikis-auto-captions`, port 8001).
- This is a **standalone tool with its own venv**, independent of [Kikis Shorts Tool](../Kikis_Shorts_Tool) — don't assume shared state, shared `data/`, or a shared virtualenv between the two.

## Why re-transcribe instead of reusing Shorts Tool's transcript

This was a deliberate decision, not an oversight: once a clip is cut/trimmed/reordered in an editor, mapping "point in the final export" back to "point in the original VOD transcript" is a real alignment problem with no clean solution. Re-transcribing the actual exported file guarantees captions match whatever's actually in the final cut, including edits. Don't try to "optimize" this into pulling word timings from the Shorts Tool's cached transcript instead — that was considered and rejected.

## Same GPU/CUDA pattern as Shorts Tool

`app/caption_words.py` uses the identical `nvidia-cublas-cu12`/`nvidia-cudnn-cu12` + `os.add_dll_directory()` wiring and automatic CPU fallback as [Kikis Shorts Tool](../Kikis_Shorts_Tool)'s `app/transcribe.py` — see that project's `CLAUDE.md` for the full rationale if this breaks. The two implementations are independent copies (separate venvs), not shared code, so a fix in one does not propagate to the other automatically.

## Caption styling is ASS override tags, not a real "highlight" renderer

The word-highlight effect in `app/ass_builder.py` works by emitting one `Dialogue` line per spoken word, each with the currently-spoken word wrapped in a `\c` color-override tag. There's no single "highlight the Nth word" primitive being toggled — every word-group/timing change regenerates the full line set. If highlighting looks off (wrong word lit, wrong timing), check the per-word `Dialogue` line boundaries in the generated `.ass`, not just the `WORDS_PER_GROUP` grouping logic.

Position is also an override tag, not a Style-level default: every line carries an explicit `{\an5\pos(x,y)}` computed from `pos_x_frac`/`pos_y_frac` × the real video resolution. The Style block's own Alignment/Margin fields are just a fallback and are effectively unused once `\pos` is present — don't try to reposition captions by editing the Style line, it won't do anything.

## Job lifecycle is two distinct phases, not one pipeline

A job now has two independent background-thread phases, each with its own heartbeat:
1. `jobs.create_job` → `pipeline.transcribe_pipeline` — probe, transcribe, cache `words.json`, extract a preview still frame (`thumbnail.jpg`). Terminal status: `transcript_ready` (or `error`).
2. `jobs.render_job` → `pipeline.render_pipeline` — load cached `words.json`, build `.ass`, burn onto the full video. Terminal status: `done` (or `error`).

`render_job` can be called any number of times against the same `job_id` (guarded to only run when status is `transcript_ready`, `done`, or `error`) — it always reads whatever's currently in `words.json` and overwrites the same output file, so restyling or re-burning after a transcript edit never re-pays GPU transcription. The frontend cache-busts the `<video>` src with a timestamp query param to see each new render.

If you change the `words.json` schema (currently `video_path`, `width`, `height`, `duration`, `words`), every reader of it (`render_pipeline`, `generate_style_preview`, the `/words` GET/PUT endpoints) needs to agree — there's no migration path, cache files are per-job scratch data under `data/<job_id>/` and safe to discard.

## Style preview is not an approximation — it's the real renderer on one frame

`pipeline.generate_style_preview` takes the first `words_per_group` words from the **real cached transcript** (not placeholder text), builds a real `.ass` via the same `ass_builder.build_ass` used for the actual burn, and runs it through `burn.burn_preview_frame` (same `ffmpeg subtitles` filter, just `-loop 1` on a still image instead of the full video). This was a deliberate fix for a prior CSS-approximation preview that didn't visually match the final output — don't reintroduce a CSS-based preview; if the preview and the real burn ever look different, that's a bug in this shared code path, not two things to keep in sync by hand.

The preview frame itself (`thumbnail.jpg`) is extracted once during `transcribe_pipeline` and reused for every subsequent style-preview call — don't re-extract it per request, that's an unnecessary full video seek+decode on every keystroke/drag.

## Transcript editing is per-word, not free-form

The frontend renders each cached word as an individually `contenteditable` span (`static/app.js` `renderTranscriptEditor`) and PUTs the *entire* words array back to `/api/jobs/{id}/words` on blur — only `word` text changes, `start`/`end` stay fixed to what Whisper produced. This was an intentional scope limit: fixing mis-transcribed words is supported, splitting/merging words or re-timing them is not. Don't build free-form textarea editing on top of this without re-deriving per-word timestamps, which is a much harder problem (word-level alignment).

## Font size / letter spacing are Style-level ASS fields

`ass_builder.build_ass` takes `font_size` (falls back to `max(28, height*0.05)` if `None` — that's the "auto" the UI shows) and `letter_spacing` (ASS `Spacing` field, default 0). Both apply uniformly to the whole style, not per-run overrides — there's no per-word size/spacing variation.

## ALL CAPS defaults on

`settings.all_caps` (env `ALL_CAPS`) defaults to `true` — this was an explicit user preference, not an oversight. Uppercasing happens in `pipeline.render_pipeline`/`generate_style_preview` right before building the `.ass` (on a copy of the word list, not in the cached `words.json`), so toggling it doesn't require re-transcription either.
