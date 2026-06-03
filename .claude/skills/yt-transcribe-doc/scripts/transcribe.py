#!/usr/bin/env python
"""
Download YouTube audio locally (residential IP bypasses Modal cloud-IP block),
transcribe via deployed Modal WhisperX, emit <slug>.transcript.json + <slug>.blocks.json.

Usage:
  python transcribe.py <url_or_id> [<url_or_id> ...] [--out DIR]

Requires: yt-dlp, ffmpeg on PATH, modal (configured creds), and the deployed
Modal app "modal-whisper-transcribe" with class "WhisperX".

Prints one line per video:  MANIFEST <json>
"""
import json, os, re, sys, glob, tempfile, unicodedata

def slugify(title: str) -> str:
    if not title:
        return "transcript"
    # strip emoji / symbols, keep letters (incl. umlauts), digits, space, dash
    t = "".join(c for c in title if unicodedata.category(c)[0] in ("L", "N") or c in " -_")
    # transliterate German umlauts to ascii for filename safety
    repl = {"ä":"ae","ö":"oe","ü":"ue","ß":"ss","Ä":"Ae","Ö":"Oe","Ü":"Ue"}
    t = "".join(repl.get(c, c) for c in t)
    t = re.sub(r"[^A-Za-z0-9 _-]", "", t)
    t = re.sub(r"\s+", "-", t.strip())
    t = re.sub(r"-{2,}", "-", t).strip("-_")
    return (t or "transcript")[:120]

def hms(s):
    s = int(s or 0)
    return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

def mkblocks(segs, block=30):
    out, cur = [], None
    for seg in segs:
        t = (seg.get("text") or "").strip()
        if not t:
            continue
        if not cur or seg["start"] - cur["s"] >= block:
            cur = {"s": seg["start"], "parts": [t]}
            out.append(cur)
        else:
            cur["parts"].append(t)
    return [{"t": hms(b["s"]), "text": " ".join(b["parts"])} for b in out]

def main():
    args = [a for a in sys.argv[1:]]
    out_dir = "."
    if "--out" in args:
        i = args.index("--out")
        out_dir = args[i + 1]
        del args[i:i + 2]
    os.makedirs(out_dir, exist_ok=True)
    if not args:
        print("ERROR: no URLs given", file=sys.stderr)
        sys.exit(2)

    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    import modal, yt_dlp
    wx = modal.Cls.from_name("modal-whisper-transcribe", "WhisperX")()

    for raw in args:
        m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", raw)
        vid = m.group(1) if m else (raw if re.match(r"^[A-Za-z0-9_-]{11}$", raw) else None)
        if not vid:
            print(f"ERROR: cannot parse video id from {raw!r}", file=sys.stderr)
            continue
        url = f"https://www.youtube.com/watch?v={vid}"
        tmp = tempfile.mkdtemp()
        outtmpl = os.path.join(tmp, "audio.%(ext)s")
        opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}],
            "quiet": True, "no_warnings": True,
            # resilience against transient network resets (ConnectionResetError 10054 etc.)
            "retries": 10, "fragment_retries": 10, "file_access_retries": 5,
            "socket_timeout": 30, "extractor_retries": 5,
        }
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
        except Exception as e:
            print(f"[{vid}] DOWNLOAD-ERROR {e}", file=sys.stderr, flush=True)
            print(f"MANIFEST_ERROR {json.dumps({'video': vid, 'url': url, 'stage': 'download', 'error': str(e)})}", flush=True)
            continue
        title = info.get("title") or vid
        dur = info.get("duration") or 0
        f = glob.glob(os.path.join(tmp, "audio.*"))[0]
        data = open(f, "rb").read()
        print(f"[{vid}] downloaded {title!r} {dur}s {len(data)}b", flush=True)

        try:
            res = wx.transcribe.remote(data)
        except Exception as e:
            print(f"[{vid}] TRANSCRIBE-ERROR {e}", file=sys.stderr, flush=True)
            print(f"MANIFEST_ERROR {json.dumps({'video': vid, 'url': url, 'stage': 'transcribe', 'error': str(e)})}", flush=True)
            continue
        res["title"], res["duration"], res["url"] = title, dur, url
        text = " ".join(s.get("text", "") for s in res.get("segments", [])).strip()
        res["text"] = text

        slug = slugify(title)
        tjson = os.path.join(out_dir, f"{slug}.transcript.json")
        bjson = os.path.join(out_dir, f"{slug}.blocks.json")
        json.dump(res, open(tjson, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        blks = mkblocks(res.get("segments", []))
        json.dump({"title": title, "url": url, "language": res.get("language"),
                   "duration": dur, "blocks": blks},
                  open(bjson, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

        manifest = {
            "slug": slug, "title": title, "url": url,
            "language": res.get("language"), "duration": dur,
            "segments": len(res.get("segments", [])), "blocks": len(blks),
            "transcript_json": tjson, "blocks_json": bjson,
            "docx": os.path.join(out_dir, f"{slug}.docx"),
            "condensed_json": os.path.join(out_dir, f"{slug}.condensed.json"),
            "condense_docx": os.path.join(out_dir, f"{slug}.condense.docx"),
        }
        print("MANIFEST " + json.dumps(manifest, ensure_ascii=False), flush=True)

if __name__ == "__main__":
    main()
