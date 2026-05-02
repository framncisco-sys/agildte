# PosAgil — aplicación Flask (Gunicorn). Pruebas locales; ajustar variables en docker-compose.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Cliente PostgreSQL (psycopg2-binary)
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Puerto interno del contenedor (coincide con Gunicorn)
EXPOSE 5000

# Detrás de nginx: encadenar X-Forwarded-* (configurar AZ_TRUST_PROXY=1 en compose)
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "2", \
     "--threads", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "app:app"]
