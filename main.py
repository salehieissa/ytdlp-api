from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import subprocess, tempfile, os, json, time

app = FastAPI()

YT_DLP_BASE = [
    "yt-dlp",
    "--no-playlist",
    "--no-check-certificates",
    "--extractor-args", "youtube:player_client=ios,web",
    "--user-agent", "com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)",
]

@app.get("/health")
def health():
    v = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
    return {"ok": True, "ytdlp_version": v.stdout.strip()}

@app.post("/extract")
async def extract(body: dict):
    url = body.get("url", "")
    if not url:
        raise HTTPException(400, "url required")

    with tempfile.TemporaryDirectory() as tmp:
        info_result = subprocess.run(
            YT_DLP_BASE + [url, "--dump-single-json", "--no-download"],
            capture_output=True, text=True, timeout=30
        )
        if info_result.returncode != 0:
            raise HTTPException(500, f"yt-dlp info failed: {info_result.stderr[:300]}")

        info = json.loads(info_result.stdout)
        title = info.get("title", "audio")
        duration = info.get("duration", 0)

        if duration > 600:
            raise HTTPException(400, "Video too long (max 10 minutes)")

        out_path = os.path.join(tmp, "audio.mp3")
        dl_result = subprocess.run(
            YT_DLP_BASE + [
                url, "-x", "--audio-format", "mp3", "--audio-quality", "5",
                "-o", out_path
            ],
            capture_output=True, text=True, timeout=120
        )
        if dl_result.returncode != 0:
            raise HTTPException(500, f"yt-dlp download failed: {dl_result.stderr[:300]}")

        with open(out_path, "rb") as f:
            data = f.read()

    return Response(
        content=data,
        media_type="audio/mpeg",
        headers={
            "X-Audio-Title": title[:60],
            "X-Audio-Duration": str(duration),
        },
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
