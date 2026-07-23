"""Crée les tables de la base (idempotent).

La base elle-même (`attrition`) est créée par le service Postgres
(docker-compose en local, Postgres managé en prod) ; ce script crée le
SCHÉMA : les tables `employes` et `predictions` telles que déclarées dans
`app/orm.py`. `create_all` ne touche pas aux tables déjà existantes.

Usage : uv run python -m scripts.create_db
"""

from app.db import Reglages, obtenir_engine
from app.orm import Base


def main() -> None:
    url = Reglages().database_url
    print(f"Base cible : {url.split('@')[-1]}")  # sans les identifiants
    Base.metadata.create_all(obtenir_engine())
    print(f"Tables créées (ou déjà présentes) : {', '.join(Base.metadata.tables)}")


if __name__ == "__main__":
    main()
