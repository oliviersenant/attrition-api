"""Insère le dataset complet (1470 employés) dans la table `employes`.

Reprend la même jointure des 3 sources que l'entraînement
(`ml.preprocessing.charger_donnees`) : la base contient exactement la donnée
de référence du modèle. Idempotent : relancer le script met à jour les
lignes existantes (upsert par clé primaire), sans doublons.

Usage : uv run python -m scripts.load_dataset
"""

from pathlib import Path

from sqlalchemy import inspect

from app.crud import compter_employes, inserer_employes
from app.db import obtenir_session
from app.orm import Employe
from ml.preprocessing import TARGET, charger_donnees

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def preparer_lignes(data_dir: str | Path = DATA_DIR) -> list[dict]:
    """Prépare les lignes prêtes à insérer (fonction pure, testable).

    La table `employes` reflète le **contrat du modèle**, pas la forme brute
    des CSV : label binarisé, augmentation en valeur numérique, et seules les
    colonnes de la table sont conservées (les constantes/redondantes de l'EDA
    mission 3 n'y ont pas leur place).
    """
    df = charger_donnees(data_dir)
    df[TARGET] = (df[TARGET] == "Oui").astype(int)  # 1 = a quitté
    col = "augementation_salaire_precedente"
    df[col] = df[col].str.replace("%", "", regex=False).str.strip().astype(float)
    colonnes_table = {colonne.key for colonne in inspect(Employe).columns}
    df = df[[colonne for colonne in df.columns if colonne in colonnes_table]]
    return df.to_dict(orient="records")


def main() -> None:
    lignes = preparer_lignes()
    session = next(obtenir_session())
    n = inserer_employes(session, lignes)
    total = compter_employes(session)
    print(f"{n} lignes insérées/mises à jour — table employes : {total} employés")


if __name__ == "__main__":
    main()
