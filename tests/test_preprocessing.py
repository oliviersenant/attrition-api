"""Tests unitaires du preprocessing (jointure, nettoyage, feature engineering).

Figent les garanties établies lors de l'empaquetage du modèle, dont le piège
pandas 3 (dtype `str` vs `object`) rencontré pendant le développement.
"""

import pandas as pd
import pytest

from ml.preprocessing import (
    COLS_A_RETIRER,
    COLS_QUALITATIVES,
    TARGET,
    FeatureEngineering,
)

FEATURES_CREEES = [
    "satisfaction_moyenne",
    "ratio_stagnation_promo",
    "ratio_anciennete_poste",
    "revenu_par_annee_exp",
]


# --- Jointure des 3 sources --------------------------------------------------


def test_jointure_1470_employes(df_brut):
    """Les jointures inner doivent redonner exactement les 1470 du notebook."""
    assert len(df_brut) == 1470


def test_jointure_sans_valeur_manquante(df_brut):
    assert df_brut.isna().sum().sum() == 0


def test_cible_binaire_desequilibree(X_y):
    """237 partants / 1233 restés — le déséquilibre 1:5 de la mission 3."""
    _, y = X_y
    assert set(y.unique()) == {0, 1}
    assert y.sum() == 237


# --- FeatureEngineering ------------------------------------------------------


def test_conversion_augmentation_depuis_texte(df_brut):
    """'11 %' (format brut des CSV) doit devenir 11.0."""
    sortie = FeatureEngineering().transform(df_brut.drop(columns=[TARGET]))
    col = sortie["augementation_salaire_precedente"]
    assert pd.api.types.is_float_dtype(col)
    assert (col >= 0).all()


def test_conversion_augmentation_depuis_nombre(df_brut):
    """L'API enverra un nombre directement : même résultat qu'avec le texte.

    (Régression du bug pandas 3 : le test de branche se fait sur
    « est-ce numérique ? », pas sur le dtype object.)
    """
    brut = df_brut.drop(columns=[TARGET])
    depuis_texte = FeatureEngineering().transform(brut)

    numerique = brut.copy()
    numerique["augementation_salaire_precedente"] = depuis_texte[
        "augementation_salaire_precedente"
    ]
    depuis_nombre = FeatureEngineering().transform(numerique)

    pd.testing.assert_series_equal(
        depuis_texte["augementation_salaire_precedente"],
        depuis_nombre["augementation_salaire_precedente"],
    )


def test_colonnes_sans_information_supprimees(df_brut):
    sortie = FeatureEngineering().transform(df_brut.drop(columns=[TARGET]))
    assert not set(COLS_A_RETIRER) & set(sortie.columns)


def test_colonnes_supprimees_optionnelles(df_brut):
    """L'API n'enverra ni id ni colonnes constantes : leur absence ne casse rien."""
    ampute = df_brut.drop(columns=[TARGET]).drop(columns=COLS_A_RETIRER)
    sortie = FeatureEngineering().transform(ampute)
    assert len(sortie) == len(ampute)


def test_features_metier_creees(df_brut):
    sortie = FeatureEngineering().transform(df_brut.drop(columns=[TARGET]))
    for feature in FEATURES_CREEES:
        assert feature in sortie.columns, feature


def test_satisfaction_moyenne_bornee(df_brut):
    """Moyenne de 4 notes sur l'échelle 1-4 → doit rester dans [1, 4]."""
    sortie = FeatureEngineering().transform(df_brut.drop(columns=[TARGET]))
    assert sortie["satisfaction_moyenne"].between(1, 4).all()


def test_transform_sans_etat(df_brut):
    """Transformer 1 ligne seule == transformer cette ligne dans le lot complet.

    C'est la propriété « sans état » qui autorise l'inférence ligne à ligne.
    """
    brut = df_brut.drop(columns=[TARGET])
    lot = FeatureEngineering().transform(brut)
    seule = FeatureEngineering().transform(brut.iloc[[7]])
    pd.testing.assert_frame_equal(seule, lot.iloc[[7]])


def test_qualitatives_presentes(df_brut):
    """Les 7 colonnes attendues par le OneHotEncoder existent dans la donnée."""
    sortie = FeatureEngineering().transform(df_brut.drop(columns=[TARGET]))
    for col in COLS_QUALITATIVES:
        assert col in sortie.columns, col


def test_augmentation_invalide_leve_une_erreur(df_brut):
    """Une valeur non convertible doit échouer bruyamment, pas silencieusement."""
    casse = df_brut.drop(columns=[TARGET]).iloc[[0]].copy()
    casse["augementation_salaire_precedente"] = "beaucoup"
    with pytest.raises(ValueError):
        FeatureEngineering().transform(casse)
