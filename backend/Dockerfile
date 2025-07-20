# Use official Python image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
# ENV GEMINI_API_KEY=AIzaSyA1nXtCYlnurEOWNirhMSXF4NImEVS_IhY

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y libglib2.0-0 libsm6 libxrender1 libxext6 && rm -rf /var/lib/apt/lists/*


# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy the rest of the backend code
COPY . .

# Expose port
EXPOSE 8080

# Run the Flask server on port 8080
CMD ["python", "geminiserver.py"] 