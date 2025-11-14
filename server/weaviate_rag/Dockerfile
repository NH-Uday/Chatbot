# /server/weaviate_rag/Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system deps if you need them (example: curl)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
 && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./  
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# uvicorn will serve FastAPI
ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
