
---

# YT Transcriber — Docker + CUDA

Transcribe cualquier video de YouTube pegando la URL.
Genera **`.txt`**, **`.srt`** y **`.json`** con segmentos (texto + timestamps).

> Backend: [faster-whisper] (CTranslate2) — soporta **GPU (CUDA)** y **CPU**.

---

## 1) Requisitos

* **Ubuntu 22.04** (host)
* **NVIDIA driver** instalado (ej: `nvidia-smi` funciona)
* **Docker** ≥ 24 (probado con 28.3.3)
* **NVIDIA Container Toolkit** (para `--gpus all`)

### Smoke test (host → contenedor con CUDA)

```bash
docker run --rm --gpus all nvidia/cuda:12.2.0-runtime-ubuntu22.04 nvidia-smi
```

Debe mostrar tu GPU dentro del contenedor.

---

## 2) Estructura del proyecto

```
yt-transcriber/
├── exporters/
│   ├── __init__.py
│   ├── srt.py
│   └── txt.py
├── outputs/              # salidas .txt .srt .json y .m4a
├── agent.py              # orquestador CLI
├── downloader.py         # descarga audio con yt-dlp
├── transcriber.py        # llama faster-whisper
├── requirements.txt
├── Dockerfile
└── .dockerignore
```

**Salidas** (por video):

* `outputs/<video_id>.txt`
* `outputs/<video_id>.srt`
* `outputs/<video_id>.json`
* `outputs/<video_id>.m4a` (audio descargado)

---

## 3) Dockerfile y .dockerignore

**Dockerfile** (base CUDA + CTranslate2, ENTRYPOINT a tu agente):

```dockerfile
FROM ghcr.io/opennmt/ctranslate2:latest-ubuntu22.04-cuda12.2

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg ca-certificates && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN python3 -m pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# IMPORTANTE: que el entrypoint sea tu agente (no el CLI de CTranslate2)
ENTRYPOINT ["python3", "/app/agent.py"]
CMD []
```

**.dockerignore** (recomendado):

```
.venv/
__pycache__/
outputs/
cache/
cookies/
.git/
```

---

## 4) Build de la imagen

```bash
docker build -t yt-transcriber:gpu .
docker inspect --format='Entrypoint: {{json .Config.Entrypoint}}' yt-transcriber:gpu
# Debe mostrar ["python3","/app/agent.py"]
```

---

## 5) Ejecutar (GPU vs CPU)

### GPU (CUDA) — recomendado

```bash
docker run --rm --gpus all \
  -v "$PWD/outputs:/app/outputs" \
  -v "$PWD/cache:/root/.cache" \
  yt-transcriber:gpu \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lang es --model small --device cuda
```

### CPU (si no quieres/no puedes usar GPU)

```bash
docker run --rm \
  -v "$PWD/outputs:/app/outputs" \
  -v "$PWD/cache:/root/.cache" \
  yt-transcriber:gpu \
  "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lang es --model small --device cpu
```

> Nota: `--model` puede ser `tiny | base | small | medium | large-v3`.
> Por defecto, en CUDA usa **`float16`**; en CPU usa **`int8`** (definido en `transcriber.py`).

---

## 6) Verificar que corre en GPU (opcional)

One-liner dentro de tu imagen:

```bash
docker run --rm --gpus all --entrypoint python3 yt-transcriber:gpu \
  -c "from faster_whisper import WhisperModel as W; W('small',device='cuda'); print('CUDA OK')"
```

Benchmark sencillo (mismo video, mismo modelo):

```bash
# GPU
/usr/bin/time -f "\nGPU real %E" docker run --rm --gpus all \
  -v "$PWD/outputs:/app/outputs" -v "$PWD/cache:/root/.cache" \
  yt-transcriber:gpu "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lang es --model medium --device cuda

# CPU
/usr/bin/time -f "\nCPU real %E" docker run --rm \
  -v "$PWD/outputs:/app/outputs" -v "$PWD/cache:/root/.cache" \
  yt-transcriber:gpu "https://www.youtube.com/watch?v=VIDEO_ID" \
  --lang es --model medium --device cpu
```

> En nuestras pruebas reales, **GPU** (RTX 4060 Ti) \~**1:09** vs **CPU** \~**5:39** con `medium`.

---

## 7) Modelos y memoria (guía rápida)

| Modelo    | VRAM aprox (FP16) | Comentario                |
| --------- | ----------------- | ------------------------- |
| tiny/base | \~1–1.3 GB        | muy rápido, menor calidad |
| small     | \~2 GB            | balance bueno             |
| medium    | \~5 GB            | más calidad               |
| large-v3  | 10–12 GB          | máxima calidad            |

* Si te falta VRAM con `large-v3`, puedes usar el modo **mixto** `int8_float16` (ver abajo).

---

## 8) Modos de precisión (idea clave)

* **`float16` (CUDA):** rápido y de alta calidad (más VRAM).
* **`int8_float16` (CUDA):** **pesos en INT8** + **activaciones en FP16** → **menos VRAM** con pequeña pérdida de calidad; ideal para `large-v3` en GPUs de 8 GB.
* **`int8` (CPU):** más compacto; más lento que GPU.

> Si agregas un flag `--compute` a tu CLI, podrás seleccionar esto explícitamente.
> Ejemplo deseado:
>
> ```bash
> --compute float16         # por defecto en CUDA
> --compute int8_float16    # menos VRAM en GPU
> --compute int8            # CPU compacto
> ```

*(Si aún no tienes ese flag, tu `transcriber.py` ya aplica automáticamente `float16` en CUDA y `int8` en CPU.)*

---

## 9) Consejos de uso

* **Normaliza la URL**: usa `https://` y evita `&t=` suelto.
* **Cache de modelos**: se guarda en `cache/` (montado como `/root/.cache` en el contenedor).
* **Repetir el mismo video**: si `*.m4a` ya existe, la descarga es instantánea.

---

## 10) Problemas comunes y soluciones

### A) “Option ‘lang’ does not exist”

Causa: el ENTRYPOINT de la imagen base ejecuta el **CLI de CTranslate2**, que se come tus flags.
Solución: deja el ENTRYPOINT en tu Dockerfile como:

```dockerfile
ENTRYPOINT ["python3","/app/agent.py"]
```

### B) “Cannot connect to the Docker daemon…”

Arranca el servicio y añade permisos a tu usuario:

```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
# Re-log o reinicia sesión
```

### C) “Sign in to confirm you’re not a bot” (YouTube)

Es una verificación de YouTube (más común en contenedores).
**Opción robusta**: exporta cookies del navegador a `cookies/youtube.txt` y (si actualizas `downloader.py`) pásalas a `yt-dlp`.

* Exportar (una forma):

  ```bash
  yt-dlp --cookies-from-browser chrome --dump-cookies cookies/youtube.txt https://www.youtube.com
  ```
* Montar en Docker:

  ```bash
  -v "$PWD/cookies:/app/cookies"
  ```
* (Requiere que `downloader.py` consuma `--cookies /app/cookies/youtube.txt`).

### D) “tag not found” al hacer `FROM ghcr.io/opennmt/ctranslate2:...`

Usa un tag válido (probado):
`ghcr.io/opennmt/ctranslate2:latest-ubuntu22.04-cuda12.2`

### E) OOM (memoria GPU)

* Usa modelo menor (`small/medium`) o
* Cambia a precisión mixta (`int8_float16`), o
* Baja `beam_size` / desactiva opciones costosas.

---

## 11) Roadmap inmediato

* **Flag `--compute`** en CLI para elegir `float16 / int8_float16 / int8`.
* **UI web mínima** con un input de URL y selectores (modelo, dispositivo, precisión),
  botón **Transcribir**, progreso y enlaces a `.srt/.txt/.json`.

---

## 12) Ejemplos rápidos

**GPU (small, español)**

```bash
docker run --rm --gpus all \
  -v "$PWD/outputs:/app/outputs" -v "$PWD/cache:/root/.cache" \
  yt-transcriber:gpu \
  "https://www.youtube.com/watch?v=MukD8Y1hRuw" \
  --lang es --model small --device cuda
```

**CPU (medium, español)**

```bash
docker run --rm \
  -v "$PWD/outputs:/app/outputs" -v "$PWD/cache:/root/.cache" \
  yt-transcriber:gpu \
  "https://www.youtube.com/watch?v=MukD8Y1hRuw" \
  --lang es --model medium --device cpu
```

---

## Créditos y licencias

* Transcripción: [faster-whisper] (CTranslate2)
* Descargas de YouTube: `yt-dlp`
* Audio: `ffmpeg`
* La imagen base CUDA/CTranslate2 sigue las licencias de sus autores.

---

[faster-whisper]: https://github.com/SYSTRAN/faster-whisper

---