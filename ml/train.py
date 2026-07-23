"""Entraîne le Pipeline complet et exporte les artefacts servis par l'API.

Sorties (dans `ml/`) :
- `model.joblib`   — le Pipeline entraîné (données brutes → predict_proba) ;
- `metadata.json`  — seuil de décision, métriques de contrôle, version.

Reproduit le protocole du notebook de la mission 3 :
- split stratifié 75/25, `random_state=42` (cellule 45) ;
- seuil de décision choisi **sur le train uniquement**, par prédictions
  out-of-fold (StratifiedKFold 5) puis maximisation du F-beta β=2 sur la
  courbe précision-rappel (cellule 58) — le test reste vierge ;
- évaluation finale sur le test au seuil optimal.

Valeurs de référence du notebook (contrôle de non-régression) :
seuil ≈ 0.417, rappel classe « Oui » ≈ 0.73, précision ≈ 0.35.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.metrics import (
    average_precision_score,
    fbeta_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_predict, train_test_split

from preprocessing import charger_donnees, construire_pipeline, separer_X_y

RANDOM_STATE = 42
TEST_SIZE = 0.25
BETA = 2  # priorité métier : rater un partant coûte plus cher qu'une fausse alerte

ML_DIR = Path(__file__).parent
DATA_DIR = ML_DIR.parent / "data" / "raw"


def choisir_seuil_f2(pipeline, X_train, y_train, cv) -> float:
    """Seuil maximisant le F-beta β=2, choisi sur des prédictions out-of-fold.

    Mécanisme anti-triche : chaque probabilité est produite par un modèle
    n'ayant PAS vu la ligne concernée (cross_val_predict) — le seuil n'est
    donc pas ajusté sur des prédictions « par cœur » du train.
    """
    proba_oof = cross_val_predict(
        pipeline, X_train, y_train, cv=cv, method="predict_proba", n_jobs=-1
    )[:, 1]
    prec, rec, thr = precision_recall_curve(y_train, proba_oof)
    fbeta = (1 + BETA**2) * prec * rec / (BETA**2 * prec + rec + 1e-9)
    return float(thr[np.nanargmax(fbeta[:-1])])


def main() -> None:
    # 1. Données : jointure des 3 sources, X brut / y binaire
    df = charger_donnees(DATA_DIR)
    X, y = separer_X_y(df)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    print(f"Données : {X.shape[0]} employés — train {X_train.shape[0]} / test {X_test.shape[0]}")

    # 2. Seuil de décision sur le train (OOF), puis fit final sur tout le train
    pipeline = construire_pipeline()
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    seuil = choisir_seuil_f2(pipeline, X_train, y_train, cv)
    print(f"Seuil optimal (F{BETA}, OOF sur train) : {seuil:.3f}")

    pipeline.fit(X_train, y_train)

    # 3. Évaluation sur le test jamais vu, au seuil optimal
    proba_test = pipeline.predict_proba(X_test)[:, 1]
    pred_test = (proba_test >= seuil).astype(int)
    metriques = {
        "rappel_oui": round(recall_score(y_test, pred_test), 3),
        "precision_oui": round(precision_score(y_test, pred_test, zero_division=0), 3),
        "f2_oui": round(fbeta_score(y_test, pred_test, beta=BETA, zero_division=0), 3),
        "pr_auc": round(average_precision_score(y_test, proba_test), 3),
    }
    print("Métriques test (classe « Oui », au seuil optimal) :", metriques)

    # 4. Ré-entraînement sur TOUTES les données avant mise en production :
    #    le seuil et les métriques ci-dessus restent la référence honnête
    #    (mesurés sur du jamais-vu), mais l'artefact servi ne gaspille pas
    #    25 % des exemples — précieux avec seulement 237 partants.
    pipeline_final = construire_pipeline()
    pipeline_final.fit(X, y)

    # 5. Export des artefacts
    joblib.dump(pipeline_final, ML_DIR / "model.joblib")
    metadata = {
        "modele": "RandomForestClassifier (Pipeline complet brut -> proba)",
        "version": "0.1.0",
        "date_entrainement": date.today().isoformat(),
        "sklearn_version": sklearn.__version__,
        "seuil_decision": round(seuil, 3),
        "beta_seuil": BETA,
        "metriques_test": metriques,
        "n_employes": int(X.shape[0]),
        "cible": "a_quitte_l_entreprise (1 = a quitté)",
    }
    (ML_DIR / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Artefacts écrits : {ML_DIR / 'model.joblib'}, {ML_DIR / 'metadata.json'}")


if __name__ == "__main__":
    main()
