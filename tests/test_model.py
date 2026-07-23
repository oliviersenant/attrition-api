"""Tests fonctionnels du Pipeline complet (données brutes → probabilité).

Figent les 3 garanties de robustesse démontrées à l'empaquetage :
inférence n=1, tolérance aux modalités inconnues, cohérence batch/unitaire.
"""

import numpy as np
from preprocessing import TARGET
from sklearn.metrics import recall_score

SEUIL_REFERENCE = 0.415  # metadata.json — recalculé par ml/train.py


def test_predict_proba_un_seul_employe(pipeline_fitte, X_y):
    """Le cas production : un employé à la fois."""
    X, _ = X_y
    proba = pipeline_fitte.predict_proba(X.iloc[[0]])
    assert proba.shape == (1, 2)
    assert 0.0 <= proba[0, 1] <= 1.0


def test_modalite_inconnue_ne_casse_pas(pipeline_fitte, X_y):
    """handle_unknown='ignore' : un métier jamais vu ne lève pas d'exception."""
    X, _ = X_y
    employe = X.iloc[[0]].copy()
    employe["poste"] = "Astronaute"
    proba = pipeline_fitte.predict_proba(employe)[0, 1]
    assert 0.0 <= proba <= 1.0


def test_batch_egal_unitaire(pipeline_fitte, X_y):
    """Prédire 10 employés d'un coup == les prédire un par un (anti-skew)."""
    X, _ = X_y
    probas_batch = pipeline_fitte.predict_proba(X.head(10))[:, 1]
    probas_unit = np.array(
        [pipeline_fitte.predict_proba(X.iloc[[i]])[0, 1] for i in range(10)]
    )
    np.testing.assert_allclose(probas_batch, probas_unit)


def test_rappel_niveau_mission_3(pipeline_fitte, X_y):
    """Garde-fou de non-régression : le rappel in-sample au seuil de référence
    doit rester au-dessus du niveau mission 3 (0.73 mesuré sur test).

    (Mesure in-sample car le pipeline de la fixture est fitté sur tout X :
    c'est un plancher grossier — la vraie évaluation vit dans ml/train.py.)
    """
    X, y = X_y
    pred = (pipeline_fitte.predict_proba(X)[:, 1] >= SEUIL_REFERENCE).astype(int)
    assert recall_score(y, pred) >= 0.73


def test_pas_de_fuite_de_la_cible(X_y):
    """La cible ne doit jamais figurer dans les features envoyées au modèle."""
    X, _ = X_y
    assert TARGET not in X.columns
