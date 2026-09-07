FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# Install system dependencies for OpenCV and document rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY backend/ /app/backend/
COPY estimator.html /app/
COPY rfp-search.html /app/
COPY logo.svg /app/
COPY style.css /app/

EXPOSE 8080

# Run FastAPI app on Cloud Run port
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
