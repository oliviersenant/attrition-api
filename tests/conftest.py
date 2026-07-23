"""Fixtures partagées de la suite de tests.

Les fixtures coûteuses (chargement des données, fit du Pipeline) sont en
`scope="session"` : calculées une fois, réutilisées par tous les tests.
"""

import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).parent.parent
sys.path.insert(0, str(RACINE))

from ml.preprocessing import (  # noqa: E402 (import après sys.path)
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
