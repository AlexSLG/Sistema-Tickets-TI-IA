# Servicio de inferencia (API + página de prueba) con los modelos entrenados.
# Antes de construir hay que tener entrenados los modelos (python -m src.training.entrenar_todo) para que exista models/<versión>/.
#   docker build -t tickets-ti-ia .
#   docker run --rm -p 8000:8000 tickets-ti-ia        ->  http://localhost:8000
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements-servicio.txt .
RUN pip install --no-cache-dir -r requirements-servicio.txt

COPY src/ src/
COPY models/ models/
COPY data/processed/tecnicos.csv data/processed/soluciones_rapidas.json data/processed/
COPY reports/figuras/ reports/figuras/
RUN mkdir -p data && touch src/__init__.py

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/salud')" || exit 1
CMD ["uvicorn", "src.service.app:app", "--host", "0.0.0.0", "--port", "8000"]
