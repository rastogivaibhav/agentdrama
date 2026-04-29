FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for audio processing (optional Kokoro TTS)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Optional: Install Kokoro TTS (commented out as it's optional)
# RUN pip install --no-cache-dir kokoro soundfile

# Copy application code
COPY agentic_office_comedy.py .
COPY characters/ ./characters/

# Create output directory
RUN mkdir -p outputs

# Expose Gradio port
EXPOSE 7860

# Health check - waits for Gradio to be responsive
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860')" || exit 1

# Default environment (can be overridden at runtime)
ENV LLM_BACKEND=lmstudio
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

CMD ["python", "agentic_office_comedy.py"]
