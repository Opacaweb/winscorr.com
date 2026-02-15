FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (for pycairo, Pillow, etc. if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy all backend files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (Railway uses $PORT anyway)
EXPOSE 8000

# Start the app
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "app:app", "--bind", "0.0.0.0:$PORT", "--timeout", "120"]
