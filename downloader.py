from __future__ import annotations
import subprocess, json, sys, pathlib

def download_audio(url: str, out_dir: str = "outputs") -> dict:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Obtén metadatos primero
    probe = subprocess.check_output([
        "yt-dlp", "-J", "--no-warnings", url
    ], text=True)
    info = json.loads(probe)
    video_id = info.get("id")
    title = info.get("title")

    # Descarga solo audio (m4a)
    out_tmpl = str(out / f"{video_id}.%(ext)s")
    subprocess.check_call([
        "yt-dlp",
        "-f", "bestaudio[ext=m4a]/bestaudio",
        "--extract-audio",
        "--audio-format", "m4a",
        "--audio-quality", "0",
        "-o", out_tmpl,
        url
    ])
    audio_path = next((p for p in out.glob(f"{video_id}.*") if p.suffix in [".m4a", ".mp3", ".webm"]), None)
    if not audio_path:
        raise RuntimeError("No se encontró el archivo de audio descargado.")
    return {"video_id": video_id, "title": title, "audio_path": str(audio_path)}
