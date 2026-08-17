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

## No caching layer

Unlike Shorts Tool, this tool has no VOD-style caching — each job re-transcribes and re-burns from scratch every run, since the whole point is operating on a specific, already-finished export file that isn't expected to be reprocessed repeatedly. Don't add caching here unprompted; it wasn't requested and doesn't fit the tool's one-shot usage pattern.
