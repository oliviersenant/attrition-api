"""Tests de la couche base de données (ORM, CRUD, alignement du mixin)."""

from donnees import EMPLOYE_VALIDE
from sqlalchemy import inspect

from app import crud
from app.orm import Employe, Prediction

RESULTAT_EXEMPLE = {
    "probabilite_depart": 0.702,
    "prediction": 1,
    "seuil": 0.415,
    "version_modele": "0.1.0",
}


def test_mixin_aligne_les_deux_tables():
    """Garantie par construction : les 25 champs métier sont identiques
    entre `employes` et `predictions` (c'est le rôle du mixin)."""
    cols_employes = {c.key for c in inspect(Employe).columns}
    cols_predictions = {c.key for c in inspect(Prediction).columns}
    metier_employes = cols_employes - {"id_employee", "a_quitte_l_entreprise"}
    metier_predictions = cols_predictions - {
        "id",
        "probabilite_depart",
        "prediction",
        "seuil",
        "version_modele",
        "created_at",
    }
    assert metier_employes == metier_predictions
    assert len(metier_employes) == 25


def test_inserer_employes_idempotent(session_db):
    """Relancer l'insertion ne crée pas de doublons (upsert par PK)."""
    lignes = [
        {**EMPLOYE_VALIDE, "id_employee": 900001, "a_quitte_l_entreprise": 1},
        {**EMPLOYE_VALIDE, "id_employee": 900002, "a_quitte_l_entreprise": 0},
    ]
    crud.inserer_employes(session_db, lignes)
    total_1 = crud.compter_employes(session_db)
    crud.inserer_employes(session_db, lignes)  # seconde passe
    total_2 = crud.compter_employes(session_db)
    assert total_1 == total_2


def test_enregistrer_et_relire_predictions(session_db):
    """Aller-retour complet : ce qu'on écrit est ce qu'on relit."""
    crud.enregistrer_predictions(session_db, [EMPLOYE_VALIDE], [RESULTAT_EXEMPLE])
    derniere = crud.lister_predictions(session_db, limite=1)[0]

    assert derniere.probabilite_depart == RESULTAT_EXEMPLE["probabilite_depart"]
    assert derniere.age == EMPLOYE_VALIDE["age"]
    assert derniere.created_at is not None  # horodatage posé par la base


def test_lister_predictions_plus_recentes_d_abord(session_db):
    resultat_2 = {**RESULTAT_EXEMPLE, "probabilite_depart": 0.111}
    crud.enregistrer_predictions(
        session_db, [EMPLOYE_VALIDE, EMPLOYE_VALIDE], [RESULTAT_EXEMPLE, resultat_2]
    )
    lignes = crud.lister_predictions(session_db, limite=2)
    assert lignes[0].id > lignes[1].id
