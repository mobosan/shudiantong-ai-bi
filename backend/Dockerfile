FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt
COPY backend backend
COPY scripts scripts
COPY config config
ENV PYTHONPATH=/app/backend PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["sh", "-c", "python scripts/init_db.py && python scripts/seed_data.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
