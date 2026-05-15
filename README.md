# Single-user YouTube -> podcast feed tool

Very lightweight FastAPI app for one person:

- paste YouTube URL
- enter one shared password
- server runs `yt-dlp` + `ffmpeg`
- mp3 is immediately downloadable
- feed gets updated at `/feed.xml`

## Local run

Prereqs: `yt-dlp`, `ffmpeg`, Python 3.11+

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export APP_PASSWORD='your-long-password'
export BASE_URL='http://localhost:8000'
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/`.

## Docker

```bash
docker build -t yt-podcast-tool .
docker run --rm -p 8000:8000 \
  -e APP_PASSWORD='your-long-password' \
  -e BASE_URL='https://your-domain.example' \
  -v $(pwd)/data:/app/data \
  yt-podcast-tool
```

## Notes

- This is intentionally single-user and minimal.
- Password gate is only on conversion action (`POST /convert`).
- Feed and audio URLs are public by default, which is normal for podcast clients.
