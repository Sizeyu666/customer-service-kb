FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_ENDPOINT=https://hf-mirror.com \
    HF_HOME=/app/hf_cache

WORKDIR /app

# 最小系统依赖：chromadb / sentence-transformers 运行所需
RUN apt-get update && apt-get install -y --no-install-recommends gcc libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖清单利用构建缓存（CPU 版 torch，避免镜像内含 CUDA）
COPY requirements.txt requirements-local-embed.txt ./
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt -r requirements-local-embed.txt

COPY app ./app
COPY data/samples ./data/samples
RUN mkdir -p data/uploads data/vector_store

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
