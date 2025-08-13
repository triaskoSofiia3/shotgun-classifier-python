# Use pre-built CPU-only PyTorch image
FROM pytorch/pytorch:2.1.2-cpu

# Create non-root user
RUN useradd --create-home appuser
WORKDIR /app

# Copy requirements (minimal)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Set permissions
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run FastAPI with Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
