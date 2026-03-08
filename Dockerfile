FROM globalinsight-api:latest

WORKDIR /app

COPY app/ ./app/
COPY opinion_mcp/ ./opinion_mcp/
COPY requirements.txt ./requirements.txt

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
