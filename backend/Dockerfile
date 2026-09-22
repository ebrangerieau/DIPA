FROM python:3.12-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Répertoire de travail
WORKDIR /app

# Dépendances Python (INSTALL_DEV=true ajoute les outils de test, utilisé en développement)
ARG INSTALL_DEV=false
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements.txt \
    && if [ "$INSTALL_DEV" = "true" ]; then pip install -r requirements-dev.txt; fi

# Code source (les fichiers .env sont exclus par .dockerignore)
COPY app ./app
COPY migrations ./migrations
COPY scripts ./scripts

# Exécution sans privilèges root
RUN useradd --system --uid 10001 --home-dir /app cockpit && chown -R cockpit /app
USER cockpit

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=4)"

# Production : un seul worker (tâches planifiées internes), en-têtes du reverse proxy acceptés
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
