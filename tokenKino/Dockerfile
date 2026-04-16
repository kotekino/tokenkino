# Usa Python 3.12 (più stabile per Docker al momento rispetto alla 3.14-dev)
FROM python:3.14-slim

WORKDIR /app

# Installiamo le dipendenze di sistema minime
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copiamo i file delle dipendenze
COPY pyproject.toml .
# Se hai un file setup.py o altri file necessari per l'installazione editabile
COPY . .

# Installiamo il pacchetto e le dipendenze
RUN pip install --no-cache-dir .

# Esponiamo la porta di FastAPI
EXPOSE 8000

# Comando per avviare l'api
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]