"""Contrats Pydantic de l'API — la frontière typée entre le monde extérieur et le modèle.

Chaque champ est typé, borné ou énuméré : toute donnée non conforme est rejetée
en 422 AVANT d'atteindre le Pipeline. Les modalités des champs catégoriels sont
celles observées dans les données d'entraînement (référentiel du OneHotEncoder) ;
les bornes numériques sont des garde-fous de vraisemblance, volontairement plus
larges que les min/max du train — un employé de 62 ans doit rester prédictible.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# --- Entrée : un employé (schéma des 3 sources SIRH / EVAL / SONDAGE) --------


class EmployeeFeatures(BaseModel):
    """Caractéristiques brutes d'un employé, telles qu'attendues par le modèle.

    N'inclut ni identifiant technique ni colonnes constantes des extraits
    d'origine : uniquement les champs dont la prédiction a besoin.
    """

    # -- Source SIRH --
    age: int = Field(ge=16, le=75, description="Âge de l'employé (années)")
    genre: Literal["F", "M"]
    revenu_mensuel: float = Field(gt=0, le=100_000, description="Revenu mensuel brut (€)")
    statut_marital: Literal["Célibataire", "Divorcé(e)", "Marié(e)"]
    departement: Literal["Commercial", "Consulting", "Ressources Humaines"]
    poste: Literal[
        "Assistant de Direction",
        "Cadre Commercial",
        "Consultant",
        "Directeur Technique",
        "Manager",
        "Représentant Commercial",
        "Ressources Humaines",
        "Senior Manager",
        "Tech Lead",
    ]
    nombre_experiences_precedentes: int = Field(ge=0, le=30)
    annee_experience_totale: int = Field(ge=0, le=60, description="Années d'expérience totale")
    annees_dans_l_entreprise: int = Field(ge=0, le=60)
    annees_dans_le_poste_actuel: int = Field(ge=0, le=60)

    # -- Source EVAL --
    satisfaction_employee_environnement: int = Field(ge=1, le=4, description="Échelle 1-4")
    note_evaluation_precedente: int = Field(ge=1, le=4, description="Échelle 1-4")
    satisfaction_employee_nature_travail: int = Field(ge=1, le=4, description="Échelle 1-4")
    satisfaction_employee_equipe: int = Field(ge=1, le=4, description="Échelle 1-4")
    satisfaction_employee_equilibre_pro_perso: int = Field(ge=1, le=4, description="Échelle 1-4")
    heure_supplementaires: Literal["Non", "Oui"]
    augementation_salaire_precedente: float = Field(
        ge=0, le=100, description="Dernière augmentation, en % (ex. 11 pour « 11 % »)"
    )

    # -- Source SONDAGE --
    nombre_participation_pee: int = Field(ge=0, le=10, description="Participations au PEE")
    nb_formations_suivies: int = Field(ge=0, le=20)
    distance_domicile_travail: float = Field(ge=0, le=500, description="Distance (km)")
    niveau_education: int = Field(ge=1, le=5, description="Échelle 1-5")
    domaine_etude: Literal[
        "Autre",
        "Entrepreunariat",
        "Infra & Cloud",
        "Marketing",
        "Ressources Humaines",
        "Transformation Digitale",
    ]
    frequence_deplacement: Literal["Aucun", "Frequent", "Occasionnel"]
    annees_depuis_la_derniere_promotion: int = Field(ge=0, le=60)
    annes_sous_responsable_actuel: int = Field(ge=0, le=60)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
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
            ]
        }
    }


# --- Sorties ------------------------------------------------------------------


class PredictionResponse(BaseModel):
    """Résultat de prédiction pour un employé."""

    probabilite_depart: float = Field(
        ge=0, le=1, description="Probabilité que l'employé quitte l'entreprise"
    )
    prediction: Literal[0, 1] = Field(
        description="1 = risque de départ (probabilité ≥ seuil), 0 sinon"
    )
    seuil: float = Field(description="Seuil de décision appliqué (politique métier, F2)")
    version_modele: str


class HealthResponse(BaseModel):
    """État de l'API et du modèle chargé."""

    status: Literal["ok"]
    version_modele: str
    seuil: float
    date_entrainement: str


class PredictionRecord(EmployeeFeatures):
    """Ligne de la table `predictions` (relecture d'audit) : l'input tracé
    tel que reçu + l'output rendu + le contexte de décision."""

    id: int
    probabilite_depart: float
    prediction: Literal[0, 1]
    seuil: float
    version_modele: str
    created_at: datetime

    model_config = {"from_attributes": True}
