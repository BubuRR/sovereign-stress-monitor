# Lightweight Python 3.11 base image
FROM python:3.11-slim

# System deps for building C extensions (numpy/scipy/ruptures)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies from requirements.txt (better layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy full repository into the container
COPY . .

# Ports: 8000 FastAPI backend, 8501 Streamlit dashboard
EXPOSE 8000
EXPOSE 8501

# Default: API gateway
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
