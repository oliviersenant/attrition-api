"""Opérations de lecture/écriture en base — l'unique passage vers les tables.

L'API et les scripts passent tous par ces fonctions : un seul endroit à
auditer pour savoir ce qui entre et sort de la base.
"""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orm import Employe, Prediction


def enregistrer_predictions(
    session: Session, entrees: Iterable[dict], resultats: Iterable[dict]
) -> list[Prediction]:
    """Trace chaque échange avec le modèle : input reçu + output rendu.

    Exigence du brief : toute interaction avec le modèle passe par la base.
    Le commit est atomique — un lot batch est tracé entièrement ou pas du tout.
    """
    lignes = [
        Prediction(**entree, **resultat)
        for entree, resultat in zip(entrees, resultats, strict=True)
    ]
    session.add_all(lignes)
    session.commit()
    return lignes


def lister_predictions(session: Session, limite: int = 50) -> list[Prediction]:
    """Les prédictions les plus récentes d'abord (relecture d'audit)."""
    requete = select(Prediction).order_by(Prediction.id.desc()).limit(limite)
    return list(session.scalars(requete))


def inserer_employes(session: Session, lignes: Iterable[dict]) -> int:
    """Insère (ou met à jour) le dataset de référence. Idempotent par PK."""
    n = 0
    for ligne in lignes:
        session.merge(Employe(**ligne))  # merge = upsert sur la clé primaire
        n += 1
    session.commit()
    return n


def compter_employes(session: Session) -> int:
    return len(list(session.scalars(select(Employe.id_employee))))
