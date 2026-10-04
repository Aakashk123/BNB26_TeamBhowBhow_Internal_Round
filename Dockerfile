FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend:/app/sdk/python
WORKDIR /app
COPY backend/requirements.lock /app/backend/requirements.lock
RUN pip install --no-cache-dir pip==26.2.1 && pip install --no-cache-dir -r /app/backend/requirements.lock
COPY backend /app/backend
COPY config /app/config
COPY sdk/python /app/sdk/python
COPY scripts /app/scripts
COPY demo /app/demo
RUN useradd -m -u 10001 modelledger && mkdir -p /app/.runtime && chown -R modelledger:modelledger /app
USER modelledger
EXPOSE 8000
CMD ["sh", "/app/scripts/start_backend.sh"]
