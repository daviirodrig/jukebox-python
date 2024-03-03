import contextlib
import io
import os.path
from hashlib import md5

import ffmpeg
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from yt_dlp import YoutubeDL as yt_dlp
from yt_dlp import utils
import psutil
import ipaddress
import socket

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def ip_rotator(ip_list):
    ip_index = 0
    while True:
        yield ip_list[ip_index]
        ip_index = (ip_index + 1) % len(ip_list)


def get_ips(interface):
    interface_addrs = psutil.net_if_addrs().get(interface) or []
    ipv6s = [ipaddress.ip_address(addr.address) for addr in interface_addrs if addr.family == socket.AF_INET6]
    global_ips = [ip for ip in ipv6s if ip.is_global]
    return global_ips


@app.get("/python/audio/jukebox/{trackSearch:path}")
def get_audio(trackSearch: str):
    if not trackSearch:
        return Response(status_code=400)
    track_hash = md5(trackSearch.encode("utf-8")).hexdigest()
    filename = f"./cache/{track_hash}.mp3"

    if os.path.isfile(filename):
        print("Found cached file")
        with open(filename, "rb") as f:
            ffbuffer = io.BytesIO(f.read())
            return Response(
                content=ffbuffer.getvalue(),
                media_type="audio/mp3",
                headers={
                    "Content-Disposition": f"attachment; filename={track_hash}.mp3",
                },
                status_code=200,
            )
    ip = next(ip_rotator(get_ips(os.environ.get("INTERFACE"))))
    yt_dlp_config = {
        "extract_flat": "discard_in_playlist",
        "final_ext": "mp3",
        "format": "mp3/bestaudio/best",
        "fragment_retries": 10,
        "ignoreerrors": "only_download",
        "max_downloads": 1,
        "max_filesize": 104857600,
        "noplaylist": True,
        "source_address": ip,
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

    with contextlib.redirect_stdout(buffer), yt_dlp(yt_dlp_config) as y:
        try:
            y.download(f"https://music.youtube.com/search?q={trackSearch}&sp=EgWKAQIIAWoKEAoQAxAEEAkQBQ%3D%3D")
        except utils.MaxDownloadsReached:
            pass

    process = (
        ffmpeg.input("pipe:")
        .output(filename=filename, c="libmp3lame", audio_bitrate="128k")
        .run_async(pipe_stdin=True, overwrite_output=True)
    )

    process.communicate(input=buffer.getbuffer())

    with open(filename, "rb") as f:
        ffbuffer = io.BytesIO(f.read())

    return Response(
        content=ffbuffer.getvalue(),
        media_type="audio/mp3",
        headers={
            "Content-Disposition": f"attachment; filename={track_hash}.mp3",
        },
        status_code=200,
    )
