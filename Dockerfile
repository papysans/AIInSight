FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt ./requirements.txt

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY opinion_mcp/ ./opinion_mcp/

RUN mkdir -p /app/cache /app/outputs /app/runtime/xhs/data /app/runtime/xhs/images

EXPOSE 18061

CMD ["python", "-m", "opinion_mcp.server", "--host", "0.0.0.0", "--port", "18061"]
