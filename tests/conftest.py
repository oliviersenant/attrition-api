"""Fixtures partagées de la suite de tests.

Les fixtures coûteuses (chargement des données, fit du Pipeline, création du
schéma DB) sont en `scope="session"` : calculées une fois, réutilisées partout.

Base de tests : le Postgres du service CI si `TEST_DATABASE_URL` est définie,
sinon SQLite en mémoire (rapide, zéro dépendance en local) — même ORM, mêmes
tables : SQLAlchemy fait l'abstraction.
"""

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

RACINE = Path(__file__).parent.parent
sys.path.insert(0, str(RACINE))

from app.orm import Base  # noqa: E402 (import après sys.path)
from ml.preprocessing import (  # noqa: E402
    charger_donnees,
    construire_pipeline,
    separer_X_y,
)


@pytest.fixture(scope="session")
def df_brut():
    """Les 3 sources jointes (1470 employés), comme reçues par le pipeline."""
    return charger_donnees(RACINE / "data" / "raw")


@pytest.fixture(scope="session")
def X_y(df_brut):
    return separer_X_y(df_brut)


@pytest.fixture(scope="session")
def pipeline_fitte(X_y):
    """Pipeline complet entraîné une fois pour toute la session de tests."""
    X, y = X_y
    pipeline = construire_pipeline()
    pipeline.fit(X, y)
    return pipeline


# --- Base de données de test -------------------------------------------------


@pytest.fixture(scope="session")
def engine_db():
    """Engine de test : Postgres du CI (TEST_DATABASE_URL) ou SQLite mémoire."""
    url = os.environ.get("TEST_DATABASE_URL", "sqlite://")
    if url.startswith("sqlite"):
        # StaticPool : une seule connexion partagée, sinon chaque session
        # verrait une base :memory: différente (donc vide).
        engine = create_engine(
            url, connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    else:
        engine = create_engine(url)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def session_db(engine_db):
    """Une session neuve par test, toujours refermée."""
    session = sessionmaker(bind=engine_db, expire_on_commit=False)()
    yield session
    session.close()
