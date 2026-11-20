# t531 (20/11/2026) — couche hébergée, pièce ② : Deepotus VideoGen dans un conteneur Linux (VPS Hostinger).
# Plan : docs/superpowers/plans/2026-11-20-couche-hebergee-vps.md ; déploiement : deploiement/vps/README.md.
# Le même backend et la même coque web que l'app Windows ; ffmpeg et Chromium viennent de Debian.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      ffmpeg chromium fonts-dejavu-core fonts-liberation fonts-noto-color-emoji \
      openssh-client ca-certificates tini \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/app backend/app
COPY frontend/dist frontend/dist
COPY vendor vendor
COPY --chmod=755 deploiement/vps/chromium-conteneur /usr/local/bin/chromium-conteneur

# Un utilisateur sans privilèges (uid 1000 = le propriétaire de /srv/deepotus/data sur le VPS).
RUN useradd --uid 1000 --create-home --shell /usr/sbin/nologin deepotus \
 && mkdir -p /data /depot \
 && chown deepotus:deepotus /data
USER deepotus

ENV DEEPOTUS_DATA_DIR=/data \
    DEEPOTUS_NAVIGATEUR=/usr/local/bin/chromium-conteneur \
    HOST=127.0.0.1 \
    PORT=8765

WORKDIR /app/backend
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=4).status == 200 else 1)"]

# Écoute la boucle locale SEULEMENT : le conteneur partage le réseau de l'hôte (docker-compose.yml) et seul Caddy,
# sur la même machine, l'atteint. --no-proxy-headers : l'adresse cliente reste celle de Caddy (127.0.0.1) ; les gardes
# du backend ne voient jamais X-Forwarded-For. Pas de --reload.
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8765", "--no-proxy-headers", "--workers", "1"]
