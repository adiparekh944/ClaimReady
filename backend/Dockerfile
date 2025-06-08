# Use official Python image
FROM python:3.10-slim

# Install system dependencies for PyAudio and other builds
RUN apt-get update && apt-get install -y gcc libasound2-dev portaudio19-dev libportaudio2 libportaudiocpp0 ffmpeg

# Set work directory
WORKDIR /app

# Copy requirements first
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy full backend codebase
COPY backend/ .

# Expose Flask port
EXPOSE 8080

# Run your API
CMD ["python", "api.py"]