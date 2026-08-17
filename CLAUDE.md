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

## Words are cached per job — transcription and rendering are separate stages

`app/pipeline.py` has three entry points: `run_pipeline` (fresh run: probe → transcribe → cache `words.json` in the job dir → render), `render_captions` (build `.ass` + burn, shared by both paths), and `rerender_pipeline` (loads the cached `words.json`, skips transcription entirely, re-renders with new style params). This exists specifically so style tweaks (font, caps, word count, position) after a run don't re-pay the GPU transcription cost — `jobs.rerender_job` reuses the *same* `job_id` and overwrites the *same* output file, so the frontend just needs a cache-busting query param on the `<video>` src to see the new render.

If you change what gets cached in `words.json` (currently `video_path`, `width`, `height`, `duration`, `words`), remember `rerender_pipeline` reads that same schema back — keep them in sync, there's no migration path for old cache files (they're per-job scratch data under `data/<job_id>/`, safe to just discard if the schema changes).

## ALL CAPS defaults on

`settings.all_caps` (env `ALL_CAPS`) defaults to `true` — this was an explicit user preference, not an oversight. Uppercasing happens in `pipeline.render_captions` right before building the `.ass` (on a copy of the word list, not in the cached `words.json`), so toggling it doesn't require re-transcription either.
