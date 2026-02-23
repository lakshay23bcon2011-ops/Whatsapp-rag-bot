FROM python:3.11-slim

LABEL maintainer="WhatsApp RAG Bot"
LABEL description="Personalized AI chatbot that replies to WhatsApp messages sounding exactly like you"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the embedding model so it's baked into the image (optional - comment out if DISABLE_RAG=true)
# RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Copy application code
COPY . .

# Create logs directory if needed
RUN mkdir -p /app/logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run the server (use $PORT from Render)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

