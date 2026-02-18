FROM python:3.13-slim

WORKDIR /app

# Install git for vault sync
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set cloud zone defaults
ENV WORK_ZONE=cloud
ENV WEB_ENABLED=true
ENV WEB_PORT=8000
ENV FILE_WATCH_ENABLED=false
ENV AUTO_APPROVE_THRESHOLD=1.0

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/health'); assert r.status_code == 200"

CMD ["python", "main.py", "--dashboard-only"]
