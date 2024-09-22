import contextlib
import io
import os
import re
from hashlib import md5

from ffmpeg import FFmpeg, Progress
from fastapi import FastAPI, Response, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from yt_dlp import YoutubeDL as yt_dlp
from yt_dlp import utils

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def get_chunk(file_path: str, start: int, end: int):
    with open(file_path, "rb") as f:
        f.seek(start)
        return f.read(end - start + 1)


@app.get("/python/audio/jukebox/{trackSearch:path}")
def get_audio(request: Request, trackSearch: str):
    if not trackSearch:
        return Response(status_code=400)

    track_hash = md5(trackSearch.encode("utf-8")).hexdigest()
    filename = f"./cache/{track_hash}.mp3"

    if os.path.isfile(filename):
        file_size = os.path.getsize(filename)
        range_header = request.headers.get("Range")
        if range_header:
            range_match = re.search(r"bytes=([0-9]+)-([0-9]*)", range_header)
            if range_match:
                start = int(range_match.group(1))
                end = range_match.group(2)
                end = int(end) if end else file_size - 1
                if start >= file_size or end >= file_size:
                    raise HTTPException(status_code=416, detail="Requested Range Not Satisfiable")
                chunk = get_chunk(filename, start, end)
                content_length = end - start + 1
                headers = {
                    "Content-Range": f"bytes {start}-{end}/{file_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(content_length),
                    "Content-Type": "audio/mpeg",
                }
                return StreamingResponse(io.BytesIO(chunk), status_code=206, headers=headers)
        else:
            headers = {"Content-Length": str(file_size), "Content-Type": "audio/mpeg"}
            return StreamingResponse(io.BytesIO(get_chunk(filename, 0, file_size - 1)), headers=headers)

    yt_dlp_config = {
        "extract_flat": "discard_in_playlist",
        "format": "bestaudio.3",
        "fragment_retries": 10,
        "ignoreerrors": "only_download",
        "max_downloads": 1,
        "max_filesize": 104857600,
        "noplaylist": True,
        "source_address": "::",
        "outtmpl": filename,
        "logtostderr": True,
        "username": "oauth2",
        "password": "",
        "playlistend": 1,
        "retries": 10,
    }
    buffer = io.BytesIO()

    with contextlib.redirect_stdout(buffer), yt_dlp(yt_dlp_config) as y:  # type: ignore
        try:
            y.download(f"https://music.youtube.com/search?q={trackSearch}&sp=EgWKAQIIAWoKEAoQAxAEEAkQBQ%3D%3D")
        except utils.MaxDownloadsReached:
            pass

    # final_file = process_ffmpeg(filename, buffer)
    if os.path.isfile(filename):
        with open(filename, "rb") as f:
            file_size = os.path.getsize(filename)
            headers = {"Content-Length": str(file_size), "Content-Type": "audio/mpeg"}
            return StreamingResponse(io.BytesIO(f.read()), headers=headers)
    else:
        raise HTTPException(status_code=500, detail="Error processing audio")

def process_ffmpeg(filename: str, buffer: io.BytesIO) -> str:
    process = FFmpeg().option("y").input("pipe:0").output(filename, {"b:a": "128k", "c:a": "libmp3lame"})

    @process.on("progress")
    def _(progress: Progress):
        print(progress)

    process.execute(buffer.getvalue())

    return filename
