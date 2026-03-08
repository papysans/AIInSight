FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    git \
    libffi-dev \
    libgl1 \
    libglib2.0-0 \
    libjpeg62-turbo-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    make \
    pkg-config \
    python3-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY opinion_mcp/ ./opinion_mcp/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
