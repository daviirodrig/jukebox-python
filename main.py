import contextlib
import io

import ffmpeg
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL as yt_dlp
from yt_dlp import utils

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/python/audio/jukebox/{trackSearch}")
async def get_audio(trackSearch: str):
    if not trackSearch:
        return Response(status_code=400)
    yt_dlp_config = {
        "extract_flat": "discard_in_playlist",
        "final_ext": "mp3",
        "format": "mp3/bestaudio/best",
        "fragment_retries": 10,
        "ignoreerrors": "only_download",
        "max_downloads": 1,
        "max_filesize": 104857600,
        "noplaylist": True,
        "outtmpl": "-",
        "logtostderr": True,
        "playlistend": 1,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "retries": 10,
    }
    buffer = io.BytesIO()

    with contextlib.redirect_stdout(buffer), yt_dlp(yt_dlp_config) as y:  # type: ignore
        try:
            y.download(
                f"https://music.youtube.com/search?q={trackSearch}&sp=EgWKAQIIAWoKEAoQAxAEEAkQBQ%3D%3D"
            )
        except utils.MaxDownloadsReached:
            pass

    process = (
        ffmpeg.input("pipe:")
        .output(filename="./compress.tmp.mp3", c="libmp3lame", audio_bitrate="128k")
        .run_async(pipe_stdin=True, overwrite_output=True)
    )

    process.communicate(input=buffer)

    with open("./compress.tmp.mp3", "rb") as f:
        ffbuffer = io.BytesIO(f.read())

    print(len(ffbuffer.getvalue()) / 1024)

    return Response(
        content=ffbuffer.getvalue(),
        media_type="audio/mp3",
        headers={
            "Content-Disposition": f"attachment; filename={trackSearch}.mp3",
        },
        status_code=200,
    )
