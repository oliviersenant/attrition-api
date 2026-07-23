"""Tests fonctionnels de l'API (endpoints, validation Pydantic, cohérence).

Le TestClient est utilisé en context manager pour déclencher le `lifespan`
(chargement réel de l'artefact `ml/model.joblib`) : on teste l'API telle
qu'elle démarre en production, pas un mock.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app

EMPLOYE_VALIDE = {
    "age": 41,
    "genre": "F",
    "revenu_mensuel": 5993,
    "statut_marital": "Célibataire",
    "departement": "Commercial",
    "poste": "Cadre Commercial",
    "nombre_experiences_precedentes": 8,
    "annee_experience_totale": 8,
    "annees_dans_l_entreprise": 6,
    "annees_dans_le_poste_actuel": 4,
    "satisfaction_employee_environnement": 2,
    "note_evaluation_precedente": 3,
    "satisfaction_employee_nature_travail": 4,
    "satisfaction_employee_equipe": 1,
    "satisfaction_employee_equilibre_pro_perso": 1,
    "heure_supplementaires": "Oui",
    "augementation_salaire_precedente": 11,
    "nombre_participation_pee": 0,
    "nb_formations_suivies": 0,
    "distance_domicile_travail": 1,
    "niveau_education": 2,
    "domaine_etude": "Infra & Cloud",
    "frequence_deplacement": "Occasionnel",
    "annees_depuis_la_derniere_promotion": 0,
    "annes_sous_responsable_actuel": 5,
}


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # context manager => lifespan exécuté
        yield c


# --- /health -----------------------------------------------------------------


def test_health(client):
    reponse = client.get("/health")
    assert reponse.status_code == 200
    corps = reponse.json()
    assert corps["status"] == "ok"
    assert 0 < corps["seuil"] < 1


# --- /predict : cas nominal --------------------------------------------------


def test_predict_nominal(client):
    reponse = client.post("/predict", json=EMPLOYE_VALIDE)
    assert reponse.status_code == 200
    corps = reponse.json()
    assert 0.0 <= corps["probabilite_depart"] <= 1.0
    assert corps["prediction"] in (0, 1)


def test_predict_decision_coherente_avec_seuil(client):
    """La décision renvoyée doit être exactement proba >= seuil."""
    corps = client.post("/predict", json=EMPLOYE_VALIDE).json()
    attendu = int(corps["probabilite_depart"] >= corps["seuil"])
    assert corps["prediction"] == attendu


def test_predict_profil_a_risque_detecte(client):
    """L'employé exemple (vrai partant de la mission 3 : heures sup,
    faible satisfaction) doit être signalé à risque."""
    corps = client.post("/predict", json=EMPLOYE_VALIDE).json()
    assert corps["prediction"] == 1


# --- /predict : validation (la frontière rejette avant le modèle) ------------


def test_champ_manquant_422(client):
    incomplet = {k: v for k, v in EMPLOYE_VALIDE.items() if k != "age"}
    assert client.post("/predict", json=incomplet).status_code == 422


def test_age_hors_bornes_422(client):
    assert (
        client.post("/predict", json={**EMPLOYE_VALIDE, "age": -5}).status_code == 422
    )


def test_satisfaction_hors_echelle_422(client):
    casse = {**EMPLOYE_VALIDE, "satisfaction_employee_equipe": 9}
    assert client.post("/predict", json=casse).status_code == 422


def test_modalite_inconnue_422(client):
    """Contrat d'API strict : un poste hors référentiel est refusé ici —
    la tolérance du OneHotEncoder reste une défense de 2e ligne."""
    casse = {**EMPLOYE_VALIDE, "poste": "Astronaute"}
    assert client.post("/predict", json=casse).status_code == 422


def test_type_invalide_422(client):
    casse = {**EMPLOYE_VALIDE, "heure_supplementaires": "peut-être"}
    assert client.post("/predict", json=casse).status_code == 422


# --- /predict/batch ----------------------------------------------------------


def test_batch_nominal(client):
    reponse = client.post("/predict/batch", json=[EMPLOYE_VALIDE, EMPLOYE_VALIDE])
    assert reponse.status_code == 200
    corps = reponse.json()
    assert len(corps) == 2
    # Deux employés identiques => deux prédictions identiques
    assert corps[0] == corps[1]


def test_batch_vide_422(client):
    assert client.post("/predict/batch", json=[]).status_code == 422


def test_batch_coherent_avec_unitaire(client):
    """Même employé => même probabilité via /predict et /predict/batch."""
    unitaire = client.post("/predict", json=EMPLOYE_VALIDE).json()
    batch = client.post("/predict/batch", json=[EMPLOYE_VALIDE]).json()[0]
    assert unitaire["probabilite_depart"] == batch["probabilite_depart"]


def test_batch_un_invalide_rejette_tout(client):
    """Validation atomique : un seul employé invalide => 422 sur tout le lot."""
    casse = {**EMPLOYE_VALIDE, "age": 200}
    reponse = client.post("/predict/batch", json=[EMPLOYE_VALIDE, casse])
    assert reponse.status_code == 422
