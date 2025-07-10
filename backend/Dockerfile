# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend codebase
COPY . .

# Create necessary directories
RUN mkdir -p frames temp_uploads

# OPTIMIZATION: Pre-download YOLO models to cache them
RUN python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"

# Set environment variables for timeouts
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production
ENV REQUEST_TIMEOUT=300
ENV PROCESSING_TIMEOUT=600

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the application with timeout configurations
CMD ["python", "api.py"] 