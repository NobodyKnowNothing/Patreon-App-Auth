FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Copy requirements that are inside this context
COPY requirements.deploy.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

EXPOSE 8080
CMD ["uvicorn", "fastapi_app.main:app", "--host", "0.0.0.0", "--port", "8080", "--log-level", "debug"]