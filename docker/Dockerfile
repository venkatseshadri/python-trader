# Dockerfile for Orbiter Trading Bot
# Build from the repository root: docker build -t orbiter -f docker/Dockerfile .

FROM python:3.11-slim

# Install system dependencies for TA-Lib and other tools
RUN apt-get update && apt-get install -y 
    build-essential 
    curl 
    git 
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the entire project
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r python-trader/orbiter/requirements.txt

# Set Python path to include both directories
ENV PYTHONPATH="/app/python-trader/orbiter:/app/python-trader/ShoonyaApi-py"

# Default command (can be overridden in docker-compose or docker run)
CMD ["python", "python-trader/orbiter/main.py"]
