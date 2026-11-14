FROM docker.io/library/python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY app.py .
COPY capture/ capture/
COPY webapp/ webapp/

RUN useradd --create-home app
USER app

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5001/', timeout=5)"

# One worker only: jobs and Socket.IO rooms live in the memory of a single process.
CMD ["gunicorn", "--worker-class", "gthread", "--workers", "1", "--threads", "100", "--no-control-socket", "--bind", "0.0.0.0:5001", "app:app"]
