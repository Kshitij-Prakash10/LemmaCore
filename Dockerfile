# Failover Guardian app image. Everything the app needs at run time is in the image: no network at run time.
# Build: docker build -t failover-guardian .
# Run:   docker run --rm -p 8000:8000 failover-guardian   (then open http://127.0.0.1:8000)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    WEB_CONCURRENCY=2

WORKDIR /app
COPY requirements.txt requirements-core.txt requirements-ml.txt requirements-deploy.txt ./
RUN pip install --no-cache-dir -r requirements-deploy.txt

COPY failover ./failover
COPY config ./config
COPY models ./models
COPY data/processed ./data/processed
COPY demo_outputs ./demo_outputs

RUN useradd --create-home --uid 10001 app && chown -R app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/api/status', timeout=4)"
CMD ["sh", "-c", "exec gunicorn --workers ${WEB_CONCURRENCY} --timeout 120 --bind 0.0.0.0:${PORT} failover.app.server:app"]
