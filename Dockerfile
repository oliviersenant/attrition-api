# Image de l'API pour Hugging Face Spaces (SDK Docker, port 7860).
# Le modèle n'est PAS versionné (décision « régénération plutôt que Git LFS ») :
# il est ré-entraîné au build à partir des CSV du dépôt, de façon déterministe.

FROM python:3.12-slim

# uv : gestionnaire de dépendances (mêmes versions que le dépôt via uv.lock).
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 1. Dépendances d'abord (couche cachée tant que le lock ne change pas).
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# 2. Le code, puis génération de l'artefact du modèle.
#    On appelle directement le python du venv (pas `uv run`, qui re-synchroniserait
#    le groupe dev) : l'image de prod reste sans pytest/ruff.
COPY . .
RUN uv sync --locked --no-dev && python -m ml.train

# 3. HF Spaces attend l'app sur 0.0.0.0:7860.
EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
