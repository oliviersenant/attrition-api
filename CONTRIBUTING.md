# Conventions de contribution

## Stratégie de branches

`main` porte **toujours du code fonctionnel** (déployable). On ne développe jamais directement
dessus : chaque changement se fait sur une branche dédiée, testée, puis fusionnée par *Pull Request*.

| Préfixe | Usage | Exemple |
|---|---|---|
| `feat/` | nouvelle fonctionnalité | `feat/api-predict`, `feat/postgres-orm` |
| `fix/` | correction de bug | `fix/threshold-decision` |
| `ci/` | pipeline / config CI-CD | `ci/github-actions` |
| `docs/` | documentation | `docs/readme-deploiement` |
| `test/` | ajout / correction de tests | `test/coverage-api` |
| `chore/` | maintenance, dépendances | `chore/bump-fastapi` |

Cycle : `git switch -c feat/xxx` → commits → push → Pull Request → tests verts → merge dans `main`.

## Messages de commit

Format court et descriptif, à l'impératif : `<type>: <quoi>`
Ex. : `feat: endpoint POST /predict avec validation Pydantic`.
Types : `feat`, `fix`, `ci`, `docs`, `test`, `chore`, `refactor`.

## Versions (tags)

Versionnage sémantique `vMAJEUR.MINEUR.CORRECTIF` posé sur `main`.
Un **tag déclenche le déploiement** (voir CI/CD). Ex. : `git tag -a v0.2.0 -m "API de prédiction"`.

## Étapes de la mission → branches associées

| Étape | Branche |
|---|---|
| Empaquetage du modèle (Pipeline + train.py) | `feat/model-packaging` |
| API FastAPI | `feat/api` |
| PostgreSQL + ORM | `feat/postgres` |
| Tests Pytest | `test/suite` |
| CI/CD | `ci/github-actions` |
| Documentation | `docs/mission` |
