FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libopenblas-dev \
    libblas-dev \
    liblapack-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user
RUN useradd --create-home appuser
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies (CPU-only PyTorch) in one step
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir torch==2.1.2 torchvision==0.16.2 \
    fastapi uvicorn transformers

# Copy app code
COPY . .

# Set permissions
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
