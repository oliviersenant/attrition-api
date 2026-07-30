"""Crée les tables de la base (idempotent).

La base elle-même (`attrition`) est créée par le service Postgres
(docker-compose en local, Postgres managé en prod) ; ce script crée le
SCHÉMA : les tables `employes` et `predictions` telles que déclarées dans
`app/orm.py`. `create_all` ne touche pas aux tables déjà existantes.

Usage : uv run python -m scripts.create_db
"""

from sqlalchemy.engine import Engine

from app.db import Reglages, obtenir_engine
from app.orm import Base


def creer_tables(engine: Engine | None = None) -> list[str]:
    """Crée les tables déclarées dans app/orm.py. Renvoie leurs noms.

    `engine` est injectable (tests) ; par défaut celui de `DATABASE_URL`.
    """
    Base.metadata.create_all(engine or obtenir_engine())
    return list(Base.metadata.tables)


def main() -> None:
    url = Reglages().database_url
    print(f"Base cible : {url.split('@')[-1]}")  # sans les identifiants
    tables = creer_tables()
    print(f"Tables créées (ou déjà présentes) : {', '.join(tables)}")


if __name__ == "__main__":
    main()
