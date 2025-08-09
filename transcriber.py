from __future__ import annotations
from faster_whisper import WhisperModel
from pathlib import Path

def transcribe(audio_path: str, lang: str = "es", model_size: str = "small", device: str = "cuda"):
    model = WhisperModel(model_size, device=device, compute_type="float16" if device=="cuda" else "int8")
    segments, info = model.transcribe(audio_path, language=lang, vad_filter=True, vad_parameters={"min_silence_duration_ms": 500})

    norm = []
    for seg in segments:
        norm.append({
            "start": seg.start if seg.start is not None else 0.0,
            "end": seg.end if seg.end is not None else 0.0,
            "text": seg.text or ""
        })
    return norm, info
