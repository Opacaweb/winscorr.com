FROM python:3.11-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

CMD exec gunicorn main:app \
    --bind "[::]:$PORT" \
    --workers 3 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --log-level info