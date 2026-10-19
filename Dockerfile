# Sistema de tickets TI con IA (API, interfaz web y modelos entrenados).
# Antes de construir hay que tener entrenados los modelos (models/v1/ está en el repositorio).
#   docker compose up --build        ->  http://localhost:8000   (levanta también PostgreSQL)
#   docker build -t tickets-ti-ia .  (solo la imagen; sin DATABASE_URL usa SQLite dentro del contenedor)
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements-servicio.txt .
RUN pip install --no-cache-dir -r requirements-servicio.txt

COPY src/ src/
COPY models/ models/
COPY data/processed/ data/processed/
COPY reports/figuras/ reports/figuras/
RUN touch src/__init__.py

EXPOSE 8000
# La primera vez la app crea las tablas y carga los datos de demostración (puede tardar ~30 s)
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/salud')" || exit 1
CMD ["uvicorn", "src.service.app:app", "--host", "0.0.0.0", "--port", "8000"]
