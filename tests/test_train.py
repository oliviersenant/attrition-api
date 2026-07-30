"""Tests de l'entraînement : reproductibilité et export de l'artefact.

Répond à l'exigence du brief « les résultats doivent être reproductibles » :
`entrainer()` (graine fixe) doit retomber sur les valeurs de référence de la
mission 3, et produire un artefact chargeable par l'API.
"""

import joblib
import pytest

from app.model import ModeleAttrition
from ml.train import entrainer, exporter

DATA_DIR = "data/raw"


@pytest.fixture(scope="module")
def entrainement():
    """Entraîne une fois (coûteux) pour tout le module."""
    return entrainer(DATA_DIR)


def test_seuil_reproduit_la_mission_3(entrainement):
    """Seuil F2 ≈ 0.417 (notebook) — la graine fixe garantit la reproductibilité."""
    _, metadata = entrainement
    assert metadata["seuil_decision"] == pytest.approx(0.415, abs=0.03)


def test_rappel_non_regression(entrainement):
    """Rappel de la classe « part » au niveau mission 3 (≈ 0.73 ± marge CV)."""
    _, metadata = entrainement
    assert metadata["metriques_test"]["rappel_oui"] >= 0.65


def test_metadata_complet(entrainement):
    _, metadata = entrainement
    assert metadata["n_employes"] == 1470
    assert metadata["beta_seuil"] == 2
    assert "sklearn_version" in metadata
    assert metadata["cible"].startswith("a_quitte_l_entreprise")


def test_export_puis_rechargement(entrainement, tmp_path):
    """L'artefact exporté est rechargeable et prédit sur un employé (bout en bout)."""
    pipeline, metadata = entrainement
    exporter(pipeline, metadata, ml_dir=tmp_path)
    assert (tmp_path / "model.joblib").exists()
    assert (tmp_path / "metadata.json").exists()

    modele = ModeleAttrition.charger(tmp_path)
    assert modele.seuil == metadata["seuil_decision"]
    # Le pipeline rechargé est fonctionnel
    charge = joblib.load(tmp_path / "model.joblib")
    assert hasattr(charge, "predict_proba")


def test_artefact_manquant_erreur_explicite(tmp_path):
    """Charger depuis un dossier sans artefact lève une erreur claire, pas un
    plantage opaque plus loin."""
    with pytest.raises(FileNotFoundError, match="ml.train"):
        ModeleAttrition.charger(tmp_path)
