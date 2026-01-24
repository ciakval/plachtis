# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=PlachtIS.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Create a non-root user and db_data directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/db_data && \
    chown -R appuser:appuser /app

# Collect static files before switching to non-root user
RUN python manage.py collectstatic --noinput

USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000')" || exit 1

# Run migrations and start gunicorn
# Use exec to replace shell process so signals are properly forwarded
# Ensure db_data directory is writable
CMD mkdir -p /app/db_data && \
    python manage.py migrate && \
    exec gunicorn PlachtIS.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers 3 \
        --timeout 30 \
        --graceful-timeout 30
