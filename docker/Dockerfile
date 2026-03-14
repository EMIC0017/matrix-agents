FROM python:3.12-slim

LABEL maintainer="Neo"
LABEL project="matrix-agents"
LABEL description="Zion - Secure Agent Runtime Environment"

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Environment
ENV MATRIX_ENV=zion
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "-m", "agents.neo"]
