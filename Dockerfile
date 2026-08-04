FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium

COPY src ./src
COPY scripts ./scripts

RUN mkdir -p /app/artifacts/discovery /app/logs

CMD ["python", "scripts/run_discovery.py"]
