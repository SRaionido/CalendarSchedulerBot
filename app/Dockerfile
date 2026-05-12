# app/Dockerfile
#
# Builds the scheduler bot image from source.
# This file is never run directly — it is referenced by the compose files
# in development/ and production/.
#
# Build manually to tag a production image:
#   cd app
#   docker build -t scheduler-bot:latest .
#
# Or let the development compose file build automatically:
#   cd development && docker compose up -d --build

FROM python:3.12-slim

# Create a non-root user for security
RUN useradd -m botuser

WORKDIR /app

# System libraries required by matplotlib and Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libfreetype6-dev \
    libpng-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies as a separate cached layer.
# Only rebuilds when requirements.txt changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code.
# .env files and compose files live outside app/ and are never copied in.
COPY . .

# /app/data is mounted as a volume by the compose files so data persists
# across container restarts and is never baked into the image itself.
VOLUME ["/app/data"]

ENV DATA_DIR=/app/data \
    CALENDAR_OUTPUT_DIR=/app/data/renders \
    PYTHONUNBUFFERED=1

USER botuser

CMD ["python", "bot.py"]