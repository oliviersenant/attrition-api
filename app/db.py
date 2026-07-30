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


@lru_cache
def obtenir_engine():
    # pool_pre_ping : vérifie la connexion avant chaque emprunt au pool —
    # évite les erreurs sur connexions fermées côté serveur (idle timeout).
    return create_engine(Reglages().database_url, pool_pre_ping=True)


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
