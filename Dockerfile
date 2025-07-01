FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for video processing
RUN apt-get update && apt-get install -y \
    libopencv-dev \
    python3-opencv \
    ffmpeg \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    curl \
    wget \
    build-essential \
    cmake \
    git \
    pkg-config \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libtbb2 \
    libtbb-dev \
    libgtk2.0-dev \
    libdc1394-22-dev \
    && rm -rf /var/lib/apt/lists/*

# Install CUDA runtime (optional, uncomment for GPU acceleration)
# ENV CUDA_VERSION=11.4.0
# RUN wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-ubuntu2004.pin && \
#     mv cuda-ubuntu2004.pin /etc/apt/preferences.d/cuda-repository-pin-600 && \
#     apt-key adv --fetch-keys https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/7fa2af80.pub && \
#     add-apt-repository "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/ /" && \
#     apt-get update && apt-get install -y cuda-toolkit-11-4 && \
#     rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories
RUN mkdir -p uploads outputs static/css static/js templates

# Expose Flask port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/health || exit 1

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV FLASK_APP=app.py

# Run with gunicorn for production or app.py for development
CMD ["sh", "-c", "if [ \"$FLASK_ENV\" = \"development\" ]; then python app.py; else gunicorn --workers=4 --bind=0.0.0.0:5000 --timeout=120 app:app; fi"]
