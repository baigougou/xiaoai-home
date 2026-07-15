FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从 GitHub 下载最新源码（兼容无 git 环境）
ADD https://github.com/baigougou/xiaoai-home/archive/refs/heads/main.tar.gz /tmp/source.tar.gz
RUN tar -xzf /tmp/source.tar.gz -C /tmp && \
    cp -r /tmp/xiaoai-home-main/src ./src && \
    cp -r /tmp/xiaoai-home-main/config ./config && \
    cp -r /tmp/xiaoai-home-main/web ./web && \
    rm -rf /tmp/source.tar.gz /tmp/xiaoai-home-main

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    httpx \
    pydantic \
    python-dotenv

EXPOSE 18015

VOLUME ["/app/config"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:18015/api/health || exit 1

ENV PYTHONPATH=/app/src

CMD ["python", "-m", "uvicorn", "xiaoai_ha_bridge.main:app", "--host", "0.0.0.0", "--port", "18015"]
