FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code including Phase 4
COPY . .

# Create data directory for SQLite database
RUN mkdir -p data

# Create logs directory
RUN mkdir -p logs

# Default command (can be overridden by docker-compose)
CMD ["python3", "slinkbot_phase4.py"] 