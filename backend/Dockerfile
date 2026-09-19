FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# curl queda para el healthcheck; libpq-dev y gcc para compilar psycopg2.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# El proceso no corre como root: si alguien logra ejecutar algo dentro del
# contenedor, no tiene permisos sobre el sistema de archivos de la imagen.
RUN useradd --create-home --uid 10001 sortmatic \
    && mkdir -p /app/media /app/staticfiles \
    && chown -R sortmatic:sortmatic /app
USER sortmatic

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/salud/ || exit 1

CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && daphne -b 0.0.0.0 -p 8000 sortmatic.asgi:application"]
