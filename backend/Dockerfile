FROM python:3.12-slim

# Avoid interactive prompts during apt installs
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Copy and install Python dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright's Chromium browser + all required OS-level dependencies
RUN playwright install --with-deps chromium

# Copy backend source modules and API server
COPY src/ ./src/
COPY api.py .

# Web interface is mounted as a volume at runtime (via docker-compose)
RUN mkdir -p /app/frontend

# Expose src/ on the Python path so backend modules import without prefix
ENV PYTHONPATH=/app/src

EXPOSE 5000

CMD ["python", "api.py"]
