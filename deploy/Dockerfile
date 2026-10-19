# SKY v10.7, build only after pinning/auditing upstream dependencies.
# This is a hardening baseline, NOT an audited container or production approval.
FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements_social.txt requirements_studio.txt requirements_office.txt requirements_production.txt requirements_verified_v110.txt ./
RUN python -m pip install --no-cache-dir -c requirements_verified_v110.txt \
    -r requirements_studio.txt -r requirements_production.txt \
    'opencv-python-headless>=4.10,<5'
COPY . .
RUN mkdir -p /app/local_data /app/data && chown -R 10001:10001 /app/local_data /app/data
USER 10001:10001
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8765/api/health',timeout=3)" || exit 1
CMD ["python","-m","uvicorn","metaverse.api:app","--host","0.0.0.0","--port","8765","--workers","1"]
