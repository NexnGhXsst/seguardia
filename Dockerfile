FROM python:3.11-slim

# Set metadata
LABEL maintainer="S3-Guardian"
LABEL description="Containerized schedule-driven backup sidecar for S3"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY s3_guardian.py .

# Create temporary directory for backups, no clogging
RUN mkdir -p /tmp/s3-guardian

# Run as non-root user for security in big systems
RUN useradd -m -u 1000 guardian && \
    chown -R guardian:guardian /app /tmp/s3-guardian

USER guardian

# Health check
HEALTHCHECK --interval=5m --timeout=3s \
    CMD pgrep -f s3_guardian.py || exit 1

# Run the application
CMD ["python", "-u", "s3_guardian.py"]
