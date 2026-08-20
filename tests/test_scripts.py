"""Tests des scripts d'initialisation de la base et de la config de connexion."""

from sqlalchemy import inspect

from app.db import Reglages, normaliser_url, obtenir_engine, obtenir_session
from app.orm import Employe
from scripts.create_db import creer_tables
from scripts.load_dataset import preparer_lignes

DATA_DIR = "data/raw"


# --- load_dataset.preparer_lignes (transformation pure) ----------------------


def test_preparer_lignes_1470_employes():
    lignes = preparer_lignes(DATA_DIR)
    assert len(lignes) == 1470


def test_preparer_lignes_colonnes_du_contrat():
    """Seules les colonnes de la table (contrat du modèle) sont conservées :
    ni id/label mis à part, aucune colonne constante des CSV bruts."""
    colonnes_table = {c.key for c in inspect(Employe).columns}
    assert set(preparer_lignes(DATA_DIR)[0].keys()) == colonnes_table


def test_preparer_lignes_label_binarise():
    valeurs = {ligne["a_quitte_l_entreprise"] for ligne in preparer_lignes(DATA_DIR)}
    assert valeurs == {0, 1}


def test_preparer_lignes_augmentation_numerique():
    """« 11 % » (texte des CSV) devient un nombre avant insertion en base."""
    ligne = preparer_lignes(DATA_DIR)[0]
    assert isinstance(ligne["augementation_salaire_precedente"], float)


# --- create_db.creer_tables (schéma) -----------------------------------------


def test_creer_tables(engine_db):
    """Le script crée bien les deux tables attendues sur l'engine fourni."""
    tables = creer_tables(engine_db)
    assert set(tables) == {"employes", "predictions"}
    assert set(inspect(engine_db).get_table_names()) >= {"employes", "predictions"}


# --- app/db : configuration de connexion (sans I/O réseau) -------------------


def test_reglages_defaut():
    """La config lit une URL (env ou défaut) sans jamais se connecter."""
    assert Reglages().database_url.startswith("postgresql")


def test_normaliser_url_force_psycopg():
    """Une URL d'hébergeur (postgresql:// ou postgres://) reçoit le driver psycopg."""
    attendu = "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert normaliser_url("postgresql://u:p@host/db?sslmode=require") == attendu
    assert normaliser_url("postgres://u:p@host/db?sslmode=require") == attendu


def test_normaliser_url_laisse_intacte_si_deja_qualifiee():
    """Une URL déjà qualifiée (driver explicite) n'est pas modifiée."""
    deja = "postgresql+psycopg://u:p@host/db"
    assert normaliser_url(deja) == deja
    assert normaliser_url("sqlite://") == "sqlite://"


def test_obtenir_session_ouvre_et_ferme():
    """La dépendance FastAPI cède une session puis la referme.

    create_engine / sessionmaker / close ne déclenchent aucune connexion
    réseau tant qu'aucune requête n'est émise → testable hors base.
    """
    assert obtenir_engine() is obtenir_engine()  # mis en cache (une seule fois)
    generateur = obtenir_session()
    session = next(generateur)
    try:
        assert session is not None
    finally:
        generateur.close()  # déclenche le finally -> session.close()
