"""Chargement de l'artefact du modèle et logique de prédiction.

L'artefact (`ml/model.joblib` + `ml/metadata.json`) est produit par
`python -m ml.train` — il n'est pas versionné, il se régénère (décision
« régénération plutôt que Git LFS »). La décision au seuil vit ici, côté
service : c'est une politique métier (curseur précision/rappel), réglable
sans réentraîner le modèle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd
from sklearn.pipeline import Pipeline

# Nécessaire au chargement : joblib ne stocke que le chemin d'import de
# FeatureEngineering (`ml.preprocessing`), le module doit donc être importable.
import ml.preprocessing  # noqa: F401

ML_DIR = Path(__file__).parent.parent / "ml"


@dataclass(frozen=True)
class ModeleAttrition:
    """Le Pipeline entraîné et sa politique de décision, chargés une fois."""

    pipeline: Pipeline
    seuil: float
    version: str
    date_entrainement: str

    @classmethod
    def charger(cls, dossier: str | Path = ML_DIR) -> ModeleAttrition:
        dossier = Path(dossier)
        artefact = dossier / "model.joblib"
        if not artefact.exists():
            raise FileNotFoundError(
                f"{artefact} introuvable — lancer `python -m ml.train` pour le régénérer."
            )
        metadata = json.loads((dossier / "metadata.json").read_text(encoding="utf-8"))
        return cls(
            pipeline=joblib.load(artefact),
            seuil=float(metadata["seuil_decision"]),
            version=str(metadata["version"]),
            date_entrainement=str(metadata["date_entrainement"]),
        )

    def predire(self, employes: pd.DataFrame) -> list[dict]:
        """Probabilité de départ + décision au seuil, pour 1..n employés."""
        probas = self.pipeline.predict_proba(employes)[:, 1]
        return [
            {
                "probabilite_depart": round(float(proba), 4),
                "prediction": int(proba >= self.seuil),
                "seuil": self.seuil,
                "version_modele": self.version,
            }
            for proba in probas
        ]
