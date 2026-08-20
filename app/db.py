"""Connexion à la base (SQLAlchemy) — configurée par la variable DATABASE_URL.

La configuration suit les 12 facteurs : l'URL vient de l'environnement (ou du
fichier `.env` en local, jamais versionné). L'engine est créé paresseusement
et une seule fois (`lru_cache`) : importer ce module ne tente aucune
connexion — la base n'est touchée qu'à la première requête.
"""

from collections.abc import Generator
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


class Reglages(BaseSettings):
    """Variables d'environnement de l'application (lues aussi depuis .env)."""

    database_url: str = "postgresql+psycopg://futurisys:futurisys@localhost:5433/attrition"
    # Clé attendue dans l'en-tête X-API-Key. Défaut de DEV uniquement : en prod,
    # la vraie clé est injectée par un secret (jamais celle-ci).
    api_key: str = "dev-local-key"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def normaliser_url(url: str) -> str:
    """Force le driver psycopg (v3) sur une URL PostgreSQL sans driver explicite.

    Les hébergeurs (Neon, Render, Heroku…) fournissent des URL `postgresql://`
    (ou l'ancien `postgres://`). SQLAlchemy y associe alors par défaut le driver
    **psycopg2**, que l'on n'installe pas → `ModuleNotFoundError`. On réécrit le
    schéma pour pointer psycopg v3, ce qu'on utilise. Une URL déjà qualifiée
    (`postgresql+psycopg://`, `sqlite://`…) est laissée intacte.
    """
    for prefixe in ("postgresql://", "postgres://"):
        if url.startswith(prefixe):
            return "postgresql+psycopg://" + url[len(prefixe) :]
    return url


@lru_cache
def obtenir_engine():
    # pool_pre_ping : vérifie la connexion avant chaque emprunt au pool —
    # évite les erreurs sur connexions fermées côté serveur (idle timeout).
    return create_engine(normaliser_url(Reglages().database_url), pool_pre_ping=True)


@lru_cache
def _fabrique_sessions() -> sessionmaker:
    return sessionmaker(bind=obtenir_engine(), expire_on_commit=False)


def obtenir_session() -> Generator[Session]:
    """Dépendance FastAPI : une session par requête, toujours refermée."""
    session = _fabrique_sessions()()
    try:
        yield session
    finally:
        session.close()
