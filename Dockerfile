# Base image
FROM python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
COPY requirements_export.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements_export.txt

# Install ffmpeg for audio processing
RUN apt-get update && apt-get install -y ffmpeg

# Copy the application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/output /data

# Expose ports
EXPOSE 5000

# Command to run the application
CMD ["python", "-m", "ateker_voices"]