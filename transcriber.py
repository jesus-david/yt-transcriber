from __future__ import annotations
from faster_whisper import WhisperModel
from pathlib import Path

# Función para transcribir audio
def transcribe(audio_path: str, lang: str = "es", model_size: str = "small", device: str = "cuda", compute_type: str | None = None):

    if compute_type is None:
        compute_type = "float16" if device == "cuda" else "int8"

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments, info = model.transcribe(
        audio_path,
        language=lang,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500})

    # Normalizar segmentos
    norm = [{"start": float(s.start or 0.0), "end": float(s.end or 0.0), "text": (s.text or "").strip()} for s in segments]

    return norm, info
