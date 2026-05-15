# tools

Minimal local-first flow for YouTube → podcast RSS.

## What this repo contains

- `hello.html`: single-file static app (GitHub Pages friendly) that builds `feed.xml` from episode JSON.

## First-draft workflow (no hosted backend)

1. Convert/download audio on your laptop with `yt-dlp` + `ffmpeg`.
2. Put resulting `.mp3` files somewhere publicly reachable (GitHub Releases, S3/R2, etc.).
3. Build `episodes.json` entries for those files.
4. Open `hello.html` (or GitHub Pages version), paste the JSON, click **Build RSS**, then **Download feed.xml**.
5. Commit `feed.xml` to this repo and let GitHub Pages host it.
6. Subscribe to the feed URL from your phone podcast app.

## Example commands

```bash
# 1) Download best audio and convert to mp3
yt-dlp \
  -f 'bestaudio' \
  --extract-audio --audio-format mp3 --audio-quality 0 \
  -o 'audio/%(upload_date)s-%(id)s-%(title).120B.%(ext)s' \
  'https://www.youtube.com/watch?v=VIDEO_ID'

# 2) (Optional) inspect metadata
yt-dlp --print '%(id)s\t%(title)s\t%(upload_date)s' 'https://www.youtube.com/watch?v=VIDEO_ID'
```

## Notes

- Pure browser SPA cannot reliably fetch YouTube media streams directly due to browser/platform restrictions.
- This repo intentionally uses a local conversion step and static feed generation.
