---
name: yt-transcribe-doc
description: Transcribe one or more YouTube videos and produce Word documents — a full timestamped transcript .docx AND a condensed .condense.docx (summary + only the substantive/medical content per timestamp). Use when the user gives a YouTube URL (or several) and wants a transcript document, readable transcript, or condensed/summarized notes from a video. Triggers on "transcribe this video", "make a doc from this YouTube", "transcript docx", "condensed transcript".
---

# YouTube → Transcript + Condensed Word Docs

Pipeline: download audio locally → Modal WhisperX transcribe → full `.docx` → condensed `.condense.docx`.

**Why download locally:** YouTube blocks Modal's cloud IPs (both `youtube-transcript-api` and yt-dlp from cloud fail with bot/IP-block). Downloading audio on the local residential IP bypasses this; only the raw audio bytes go to Modal.

## Prerequisites (check once)

- `ffmpeg` on PATH.
- Python deps: `yt-dlp`, `modal` (run `python -m pip install -q yt-dlp` if missing). Modal creds configured (`.env` with `MODAL_TOKEN_ID`/`MODAL_TOKEN_SECRET`, or `~/.modal.toml`).
- Deployed Modal app `modal-whisper-transcribe` (class `WhisperX`). Verify: `python -m modal app list`.
- Node `docx` module: `cd <skill>/scripts && npm install` (one-time).

## Steps

Let `S` = this skill's `scripts/` directory. Run all commands with UTF-8 output
(`PYTHONIOENCODING=utf-8`). Pick an output dir `OUT` (default: current working dir).

### 1. Transcribe (handles all URLs in one call)

```bash
PYTHONIOENCODING=utf-8 python "S/transcribe.py" <url1> [<url2> ...] --out "OUT"
```

Each video downloads + transcribes. For every video it writes `<slug>.transcript.json`
and `<slug>.blocks.json`, and prints a line:

```
MANIFEST {"slug":..., "title":..., "url":..., "language":..., "duration":..., "segments":N, "blocks":N, "transcript_json":..., "blocks_json":..., "docx":..., "condensed_json":..., "condense_docx":...}
```

Parse every `MANIFEST` line — those paths drive the rest.

### 2. Full transcript .docx (per video)

```bash
node "S/make_docx.js" "<transcript_json>" "<docx>"
```

### 3. Condense (per video) — needs LLM judgment

For EACH video, spawn a subagent (run multiple videos in PARALLEL — one Agent call
each, in a single message) using `universal-executor`. Build its prompt from
`S/condense_prompt.md`, substituting:
- `{BLOCKS_JSON}` → the manifest `blocks_json`
- `{CONDENSED_JSON}` → the manifest `condensed_json`
- `{N}` → manifest `blocks`
- `{TITLE}` → manifest `title`

The subagent reads the blocks, strips filler, keeps only substantive/medical content,
and writes `<slug>.condensed.json` = `{ "summary": "...", "blocks": [{t,text}, ...] }`.

### 4. Condensed .docx (per video)

```bash
node "S/make_condense.js" "<blocks_json>" "<condensed_json>" "<condense_docx>"
```

### 5. Report

List, per video: title, language, duration, the two output files, and how many
blocks were kept vs total in the condensed version.

## Notes

- Slug is derived from the video title (emoji/symbols stripped, German umlauts → ascii
  for the filename only; document text keeps native umlauts).
- Block granularity: segments grouped into ~30 s blocks for readability. Change `block=`
  in `transcribe.py:mkblocks` if needed.
- Condense step drops "—" (no-content) blocks from the condensed doc but keeps every
  real timestamp.
- Non-medical videos: the condense prompt tells the subagent to keep substantive content
  generally — works for any domain, not only medical.
