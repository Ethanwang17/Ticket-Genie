FROM python:3.11-slim

# Disable Watchtower auto-updates
LABEL com.centurylinklabs.watchtower.enable="false"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser

# Create a directory for persistent data (cookies) and set ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app && chown -R appuser:appuser /app/data

USER appuser

# Define a volume for persistence
VOLUME ["/app/data"]

# Command to run the application
CMD ["python", "run_bots.py"]
