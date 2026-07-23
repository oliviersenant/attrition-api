"""Préparation des données et construction du Pipeline du modèle d'attrition.

Reproduit fidèlement le preprocessing du notebook de la mission 3
(`attrition_esn.ipynb` : fonctions `nettoyer_features`, `ajouter_features`,
`encoder_qualitatives`), refactoré en **Pipeline sklearn unique** pour garantir
l'alignement train/inférence (anti training/serving skew) :

    données brutes (schéma des 3 sources jointes) ──► probabilité d'attrition

Différence assumée avec le notebook : l'encodage one-hot utilise
`OneHotEncoder(handle_unknown='ignore')` au lieu de `pd.get_dummies`. Le
mécanisme : `get_dummies` fabrique ses colonnes à partir des modalités
*présentes dans les données reçues* — sur un seul employé en production, la
matrice produite ne ressemblerait plus à celle du fit. `OneHotEncoder`
mémorise les modalités au `fit` et encode toute nouvelle donnée dans ce
référentiel figé (modalité inconnue → vecteur nul, pas d'erreur).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

# --- Schéma des données (issu de l'EDA de la mission 3) ---------------------

TARGET = "a_quitte_l_entreprise"
COL_ID = "id_employee"

COLS_CONSTANTES = [
    "nombre_heures_travailless",
    "nombre_employee_sous_responsabilite",
    "ayant_enfants",
]  # 1 seule modalité → aucune information
COLS_QUASI_CONSTANTES = ["note_evaluation_actuelle"]  # ~tous identiques (std ≈ 0.36)
COLS_REDONDANTES = ["niveau_hierarchique_poste"]  # corr 0.95 avec revenu_mensuel

COLS_A_RETIRER = COLS_CONSTANTES + COLS_QUASI_CONSTANTES + COLS_REDONDANTES + [COL_ID]

COLS_SATISFACTION = [
    "satisfaction_employee_environnement",
    "satisfaction_employee_nature_travail",
    "satisfaction_employee_equipe",
    "satisfaction_employee_equilibre_pro_perso",
]

# Les 7 variables qualitatives one-hot encodées (liste figée : en production on
# ne peut pas se fier à un `select_dtypes` sur la donnée reçue).
COLS_QUALITATIVES = [
    "genre",
    "statut_marital",
    "departement",
    "poste",
    "heure_supplementaires",
    "domaine_etude",
    "frequence_deplacement",
]

# Hyperparamètres retenus par le RandomizedSearchCV de la mission 3 (cellule 55).
HYPERPARAMETRES_RF = {
    "n_estimators": 300,
    "max_depth": 8,
    "min_samples_leaf": 10,
    "min_samples_split": 5,
    "max_features": "log2",
    "class_weight": "balanced",
    "random_state": 42,
}


# --- Chargement / jointure des 3 sources ------------------------------------


def charger_donnees(data_dir: str | Path = "data/raw") -> pd.DataFrame:
    """Charge et joint les 3 extraits (SIRH, EVAL, SONDAGE) sur `id_employee`.

    Reproduit les cellules 4, 18 et 19 du notebook : harmonisation de la clé
    (EVAL : "E_123" → 123 ; SONDAGE : `code_sondage` renommé), puis deux
    jointures `inner` — on ne garde que les employés présents dans les 3
    sources.
    """
    data_dir = Path(data_dir)
    sirh = pd.read_csv(data_dir / "extrait_sirh.csv")
    eval_ = pd.read_csv(data_dir / "extrait_eval.csv")
    sondage = pd.read_csv(data_dir / "extrait_sondage.csv")

    eval_[COL_ID] = eval_["eval_number"].str.replace("E_", "").astype(int)
    eval_ = eval_.drop(columns=["eval_number"])

    return sirh.merge(eval_, on=COL_ID, how="inner").merge(
        sondage.rename(columns={"code_sondage": COL_ID}), on=COL_ID, how="inner"
    )


def separer_X_y(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Sépare features brutes et cible binaire (1 = a quitté, 0 = est resté)."""
    y = (df[TARGET] == "Oui").astype(int)
    X = df.drop(columns=[TARGET])
    return X, y


# --- Transformer : nettoyage + feature engineering métier -------------------


class FeatureEngineering(BaseEstimator, TransformerMixin):
    """Nettoyage et features métier, valeur par valeur (sans état, sans leakage).

    Reproduit `nettoyer_features` + `ajouter_features` du notebook :
    - conversion `augementation_salaire_precedente` "11 %" → 11.0 ;
    - suppression des colonnes constantes / redondantes / identifiantes ;
    - création des 4 features métier (satisfaction moyenne + 3 ratios).

    Aucun paramètre appris au `fit` : chaque ligne est transformée
    indépendamment, la classe est donc sûre vis-à-vis du data leakage et
    valide pour une inférence ligne à ligne.
    """

    def fit(self, X: pd.DataFrame, y=None):  # noqa: N803 (convention sklearn)
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:  # noqa: N803
        d = X.copy()

        # "11 %" → 11.0 — tolérant : l'API pourra envoyer directement un nombre.
        # (test "numérique ?" et non "object ?" : pandas 3 type le texte en `str`)
        col = "augementation_salaire_precedente"
        if pd.api.types.is_numeric_dtype(d[col]):
            d[col] = d[col].astype(float)
        else:
            d[col] = d[col].str.replace("%", "", regex=False).str.strip().astype(float)

        # Colonnes sans information (errors="ignore" : l'API n'enverra pas
        # les colonnes constantes ni l'identifiant technique).
        d = d.drop(columns=COLS_A_RETIRER, errors="ignore")

        # Features métier (row-wise), identiques au notebook (cellule 45).
        d["satisfaction_moyenne"] = d[COLS_SATISFACTION].mean(axis=1)
        d["ratio_stagnation_promo"] = d["annees_depuis_la_derniere_promotion"] / (
            d["annees_dans_l_entreprise"] + 1
        )
        d["ratio_anciennete_poste"] = d["annees_dans_le_poste_actuel"] / (
            d["annees_dans_l_entreprise"] + 1
        )
        d["revenu_par_annee_exp"] = d["revenu_mensuel"] / (
            d["annee_experience_totale"] + 1
        )
        return d

    def get_feature_names_out(self, input_features=None):  # pragma: no cover
        return None  # délégué au ColumnTransformer aval


# --- Pipeline complet --------------------------------------------------------


def construire_pipeline() -> Pipeline:
    """Assemble le Pipeline `données brutes → prédiction` (l'artefact servi).

    Trois étages :
    1. `features`  — nettoyage + feature engineering (sans état) ;
    2. `encodage`  — one-hot mémorisé au fit sur les 7 qualitatives,
       passthrough des numériques ;
    3. `modele`    — RandomForest avec les hyperparamètres figés de la
       mission 3.
    """
    encodage = ColumnTransformer(
        transformers=[
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False, dtype=int),
                COLS_QUALITATIVES,
            )
        ],
        remainder="passthrough",
        verbose_feature_names_out=False,
    )
    return Pipeline(
        steps=[
            ("features", FeatureEngineering()),
            ("encodage", encodage),
            ("modele", RandomForestClassifier(**HYPERPARAMETRES_RF)),
        ]
    )
