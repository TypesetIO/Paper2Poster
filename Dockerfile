# Use Ubuntu 22.04 as base image
FROM ubuntu:22.04

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
# Increase pip timeout and retries for network issues
ENV PIP_DEFAULT_TIMEOUT=120
ENV PIP_RETRIES=5

# Set work directory
WORKDIR /app

# Install system dependencies and add deadsnakes PPA for Python 3.11
RUN apt-get update && apt-get install -y \
    software-properties-common \
    wget \
    curl \
    git \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3.11-distutils \
    python3-pip \
    libreoffice \
    poppler-utils \
    ffmpeg \
    build-essential \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgcc-s1 \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python and pip
RUN ln -sf /usr/bin/python3.11 /usr/bin/python && \
    ln -sf /usr/bin/python3.11 /usr/bin/python3

# Install pip for Python 3.11
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.11

# Install setuptools and wheel with retries
RUN python3.11 -m pip install --no-cache-dir --upgrade pip setuptools wheel \
    --timeout 120 --retries 5

# Copy requirements first for better Docker layer caching
COPY requirements.txt pyproject.toml ./

# Install Python dependencies with retries and increased timeout
# Split into chunks to avoid timeout on large packages
RUN python3.11 -m pip install --no-cache-dir \
    --timeout 120 --retries 5 \
    numpy scipy pandas matplotlib \
    && python3.11 -m pip install --no-cache-dir \
    --timeout 120 --retries 5 \
    torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu \
    || true

# Install remaining requirements
RUN python3.11 -m pip install --no-cache-dir \
    --timeout 120 --retries 5 \
    -r requirements.txt \
    || python3.11 -m pip install --no-cache-dir \
    --timeout 120 --retries 5 \
    --use-deprecated=legacy-resolver \
    -r requirements.txt

# Copy the entire project
COPY . .

# Create necessary directories
RUN mkdir -p tmp && \
    mkdir -p contents && \
    mkdir -p tree_splits && \
    mkdir -p assets && \
    mkdir -p model_cache

# Set permissions for entrypoint script
RUN chmod +x /app/docker-entrypoint.sh && \
    chmod +x /app/start_api.py && \
    chmod +x /app/download_models.py

# Create a non-root user
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

# Switch to non-root user
USER app

# Expose port for FastAPI service
EXPOSE 6025

# Set the entrypoint
ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Default command - run the FastAPI service with startup script
CMD ["python", "/app/start_api.py", "--host", "0.0.0.0", "--port", "6025", "--workers", "1"] 