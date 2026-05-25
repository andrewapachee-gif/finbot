FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY data/ ./data/

# Create logs directory
RUN mkdir -p logs

# Set environment
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Run the bot
CMD ["python", "src/main.py"]
