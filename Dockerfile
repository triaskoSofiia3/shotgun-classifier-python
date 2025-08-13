
    FROM python:3.11-slim

    ENV PIP_NO_CACHE_DIR=1 \
        PYTHONDONTWRITEBYTECODE=1 \
        PYTHONUNBUFFERED=1
    

    RUN apt-get update && apt-get install -y --no-install-recommends \
          ca-certificates curl \
      && rm -rf /var/lib/apt/lists/*
    
    RUN useradd --create-home --shell /usr/sbin/nologin appuser
    WORKDIR /app
    

    RUN python -m pip install --upgrade pip \
       #fix numpy
     && pip install --no-cache-dir 'numpy<2' \
 
     && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
          torch==2.1.2 torchvision==0.16.2 \

     && pip install --no-cache-dir fastapi uvicorn[standard] transformers
    

    COPY . .
    RUN chown -R appuser:appuser /app
    USER appuser
    
    EXPOSE 8000
    
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
    