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


def main() -> None:
    df = charger_donnees(DATA_DIR)
    # Label texte -> binaire (même convention que l'entraînement : 1 = a quitté)
    df[TARGET] = (df[TARGET] == "Oui").astype(int)
    # "11 %" -> 11.0 : la table stocke la valeur numérique, comme l'API la reçoit
    col_augmentation = "augementation_salaire_precedente"
    df[col_augmentation] = (
        df[col_augmentation].str.replace("%", "", regex=False).str.strip().astype(float)
    )
    # La table = le contrat du modèle : les colonnes constantes/redondantes des
    # CSV bruts (aucune information, cf. EDA mission 3) ne sont pas stockées.
    colonnes_table = {colonne.key for colonne in inspect(Employe).columns}
    df = df[[colonne for colonne in df.columns if colonne in colonnes_table]]
    lignes = df.to_dict(orient="records")

    session = next(obtenir_session())
    n = inserer_employes(session, lignes)
    total = compter_employes(session)
    print(f"{n} lignes insérées/mises à jour — table employes : {total} employés")


if __name__ == "__main__":
    main()
