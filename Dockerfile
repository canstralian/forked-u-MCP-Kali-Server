# Multi-stage Dockerfile for MCP Kali Server
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_TRUSTED_HOST="pypi.org pypi.python.org files.pythonhosted.org"

# Create non-root user for security
RUN useradd -m -u 1000 -s /bin/bash mcpuser

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt || \
    pip install --no-cache-dir Flask gunicorn psycopg2-binary requests pytest mcp

# Copy application files
COPY kali_server.py mcp_server.py ./

# Change ownership to non-root user
RUN chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose API port
EXPOSE 5000

# Health check (using python instead of curl to avoid extra dependencies)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:5000/health', timeout=5)" || exit 1

# Default command (runs the API server)
CMD ["python3", "kali_server.py"]
