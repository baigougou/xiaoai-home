FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/ ./src/
COPY config/ ./config/
COPY web/ ./web/

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    httpx \
    pydantic \
    python-dotenv

EXPOSE 8000

VOLUME ["/app/config"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "uvicorn", "xiaoai_ha_bridge.main:app", "--host", "0.0.0.0", "--port", "8000"]
