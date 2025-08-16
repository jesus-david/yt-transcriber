# Base con CTranslate2 + CUDA (compatible con tu driver 575 / CUDA 12.9)
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
