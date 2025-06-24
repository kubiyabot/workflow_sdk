# Multi-stage build for Kubiya Workflow SDK Server
FROM python:3.10-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements first for better caching
COPY pyproject.toml setup.py ./
COPY kubiya_workflow_sdk/__version__.py ./kubiya_workflow_sdk/
COPY README.md ./

# Install dependencies
RUN pip install --upgrade pip && \
    pip install build && \
    python -m build --wheel

# Production stage
FROM python:3.9-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 kubiya

# Set working directory
WORKDIR /app

# Copy wheel from builder
COPY --from=builder /build/dist/*.whl /tmp/

# Install the package
RUN pip install --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl

# Copy server startup script
COPY --chown=kubiya:kubiya docker/start_server.sh /app/start_server.sh
RUN chmod +x /app/start_server.sh

# Switch to non-root user
USER kubiya

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0 \
    LOG_LEVEL=INFO

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Start the server
CMD ["/app/start_server.sh"] 