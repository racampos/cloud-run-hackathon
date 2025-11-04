# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set Python path
ENV PYTHONPATH=/app

# Set environment variables
ENV GCS_BUCKET=${GCS_BUCKET:-netgenius-artifacts-dev}
ENV REGION=${REGION:-us-central1}

# Run the job
ENTRYPOINT ["python", "main.py"]
