import hashlib
import os
import re
import subprocess
import uuid
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

APP_PASSWORD = os.getenv("APP_PASSWORD", "")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
DATA_DIR = Path(os.getenv("DATA_DIR", "data"))
AUDIO_DIR = DATA_DIR / "audio"
FEED_PATH = DATA_DIR / "feed.xml"
EPISODES_PATH = DATA_DIR / "episodes.tsv"

DATA_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Single-user YouTube Podcast Tool")
app.mount("/audio", StaticFiles(directory=AUDIO_DIR), name="audio")


HTML = """<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>YouTube -> MP3 feed updater</title>
<style>body{font-family:system-ui;max-width:860px;margin:1rem auto;padding:0 1rem}input,button{padding:.55rem;border-radius:8px}input{width:100%;box-sizing:border-box}.card{border:1px solid #ccc;padding:1rem;border-radius:12px;margin:1rem 0}</style>
</head><body>
<h1>YouTube -> MP3 feed updater</h1>
<div class='card'>
<form method='post' action='/convert'>
<label>Password</label><input name='password' type='password' required />
<label>YouTube URL</label><input name='youtube_url' placeholder='https://www.youtube.com/watch?v=...' required />
<button type='submit'>Convert + add to feed</button>
</form>
</div>
<div class='card'>
<p><a href='/feed.xml'>Open RSS feed</a></p>
<p><a href='/episodes'>View episodes</a></p>
</div>
</body></html>"""


def check_password(password: str) -> None:
    if not APP_PASSWORD:
        raise HTTPException(status_code=500, detail="APP_PASSWORD is not set")
    if password != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Bad password")


def slugify(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]+", "-", name).strip("-")[:120] or "episode"


def run_cmd(args: list[str]) -> str:
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        raise HTTPException(status_code=400, detail=proc.stderr.strip() or "command failed")
    return proc.stdout.strip()


def load_episodes() -> list[dict]:
    episodes = []
    if not EPISODES_PATH.exists():
        return episodes
    for line in EPISODES_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        title, pub_iso, guid, audio_url, audio_path = line.split("\t", 4)
        episodes.append({
            "title": title,
            "pub_iso": pub_iso,
            "guid": guid,
            "audio_url": audio_url,
            "audio_path": audio_path,
        })
    return episodes


def save_episodes(episodes: list[dict]) -> None:
    lines = ["\t".join([e["title"], e["pub_iso"], e["guid"], e["audio_url"], e["audio_path"]]) for e in episodes]
    EPISODES_PATH.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def build_feed(episodes: list[dict]) -> None:
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "My YouTube Podcast"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Single-user generated podcast feed"
    ET.SubElement(channel, "lastBuildDate").text = format_datetime(datetime.now(timezone.utc))
    for ep in sorted(episodes, key=lambda e: e["pub_iso"], reverse=True):
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = ep["title"]
        ET.SubElement(item, "guid").text = ep["guid"]
        pub_dt = datetime.fromisoformat(ep["pub_iso"])
        ET.SubElement(item, "pubDate").text = format_datetime(pub_dt)
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", ep["audio_url"])
        enclosure.set("type", "audio/mpeg")
        size = Path(ep["audio_path"]).stat().st_size if Path(ep["audio_path"]).exists() else 0
        enclosure.set("length", str(size))
    xml = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    FEED_PATH.write_bytes(xml)


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


@app.post("/convert")
def convert(password: str = Form(...), youtube_url: str = Form(...)):
    check_password(password)
    title = run_cmd(["yt-dlp", "--no-warnings", "--print", "%(title)s", youtube_url]).splitlines()[-1]
    upload_date = run_cmd(["yt-dlp", "--no-warnings", "--print", "%(upload_date)s", youtube_url]).splitlines()[-1]
    video_id = run_cmd(["yt-dlp", "--no-warnings", "--print", "%(id)s", youtube_url]).splitlines()[-1]
    dt = datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=timezone.utc)
    fname = f"{dt.strftime('%Y%m%d')}-{video_id}-{slugify(title)}.mp3"
    out_path = AUDIO_DIR / fname
    run_cmd([
        "yt-dlp", "-f", "bestaudio", "--extract-audio", "--audio-format", "mp3", "--audio-quality", "0",
        "-o", str(out_path.with_suffix(".%(ext)s")), youtube_url,
    ])
    audio_url = f"{BASE_URL}/audio/{fname}"
    guid = hashlib.sha256(f"{video_id}:{fname}".encode()).hexdigest()
    episodes = load_episodes()
    episodes = [e for e in episodes if e["guid"] != guid]
    episodes.append({"title": title, "pub_iso": dt.isoformat(), "guid": guid, "audio_url": audio_url, "audio_path": str(out_path)})
    save_episodes(episodes)
    build_feed(episodes)
    return RedirectResponse(url=f"/audio/{fname}", status_code=303)


@app.get('/feed.xml')
def feed():
    if not FEED_PATH.exists():
        build_feed(load_episodes())
    return FileResponse(FEED_PATH, media_type='application/rss+xml')


@app.get('/episodes')
def episodes(request: Request):
    rows = load_episodes()
    body = ["<h1>Episodes</h1><ul>"]
    for ep in sorted(rows, key=lambda e: e['pub_iso'], reverse=True):
        body.append(f"<li>{ep['pub_iso']} - {ep['title']} - <a href='{ep['audio_url']}'>mp3</a></li>")
    body.append("</ul><p><a href='/'>back</a></p>")
    return HTMLResponse("".join(body))


@app.get('/healthz')
def healthz():
    return Response(content='ok', media_type='text/plain')
