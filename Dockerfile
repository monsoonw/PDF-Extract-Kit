FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    git \
    wget \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements files
COPY requirements.txt /app/
COPY requirements-cpu.txt /app/
COPY runpod_requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir -r runpod_requirements.txt

# Copy the entire project
COPY . /app/

# Set the configuration path environment variable
ENV CONFIG_PATH="project/pdf2markdown/configs/pdf2markdown.yaml"

# Expose port for API
EXPOSE 8000

# Set the entrypoint
CMD ["python3", "-m", "runpod.serverless.start", "--handler", "handler.handler"] 