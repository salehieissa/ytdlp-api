from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
import subprocess, tempfile, os, json

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/extract")
async def extract(body: dict):
    url = body.get("url", "")
    if not url:
        raise HTTPException(400, "url required")

    with tempfile.TemporaryDirectory() as tmp:
        info_result = subprocess.run(
            ["yt-dlp", url, "--dump-single-json", "--no-download", "--no-playlist", "--no-check-certificates"],
            capture_output=True, text=True, timeout=20
        )
        if info_result.returncode != 0:
            raise HTTPException(500, f"yt-dlp info failed: {info_result.stderr[:200]}")

        info = json.loads(info_result.stdout)
        title = info.get("title", "audio")
        duration = info.get("duration", 0)

        if duration > 600:
            raise HTTPException(400, "Video too long (max 10 minutes)")

        out_path = os.path.join(tmp, "audio.mp3")
        dl_result = subprocess.run(
            ["yt-dlp", url, "-x", "--audio-format", "mp3", "--audio-quality", "5",
             "-o", out_path, "--no-playlist", "--no-check-certificates"],
            capture_output=True, text=True, timeout=60
        )
        if dl_result.returncode != 0:
            raise HTTPException(500, f"yt-dlp download failed: {dl_result.stderr[:200]}")

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
