# =========================
# Stage 1: Builder
# =========================
FROM python:3.11-slim as builder

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# системні залежності для збірки
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
      libxml2-dev \
      libxslt1-dev \
      libjpeg62-turbo-dev \
      zlib1g-dev \
      libglib2.0-dev \
      libgl1-mesa-dev \
      ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# requirements
COPY requirements.txt .
RUN python -m pip install "pip<24"

# збірка wheel'ів (CPU-only PyTorch + твої requirements)
RUN pip wheel --no-cache-dir --wheel-dir /wheels \
    torch==2.1.2+cpu torchvision==0.16.2+cpu \
    -f https://download.pytorch.org/whl/torch_stable.html && \
    pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt


# =========================
# Stage 2: Runtime
# =========================
FROM python:3.11-slim

ENV PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      libxml2 \
      libxslt1.1 \
      libjpeg62-turbo \
      zlib1g \
      libglib2.0-0 \
      libgl1 \
      ca-certificates curl \
  && rm -rf /var/lib/apt/lists/*

# створюємо юзера
RUN useradd --create-home --shell /usr/sbin/nologin appuser
WORKDIR /app

# ставимо wheel-и з builder stage
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* && \
    rm -rf /wheels /root/.cache /tmp/pip

# копіюємо код
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
