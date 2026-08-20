# Attrition API — Déploiement du modèle de prédiction d'attrition (Futurisys)

API de production exposant le modèle de **prédiction d'attrition des employés** développé pour
TechNova (mission précédente). Le client Futurisys veut rendre ce modèle **opérationnel** : une API
performante, testée, versionnée, traçant tous ses échanges en base de données, et déployée en CI/CD.

> **Statut :** ✅ POC fonctionnel et déployé — mission guidée OpenClassrooms (parcours AI/ML Engineer).
> **API live :** https://attrition-api-526p.onrender.com/docs (Swagger).

## Le modèle exposé

- **Tâche :** classification binaire — un employé va-t-il quitter l'entreprise ? (`a_quitte_l_entreprise`)
- **Algorithme :** `RandomForestClassifier` (scikit-learn) fine-tuné, `class_weight='balanced'`.
- **Décision :** prise au **seuil 0.415** (optimisé F-beta β=2, priorité au rappel), **pas 0.5** —
  mieux vaut une fausse alerte qu'un départ raté.
- **Performance :** rappel de la classe « part » ≈ 0.71 (≈ 7 partants détectés sur 10).
- **Entrées :** caractéristiques d'un employé issues de 3 sources (SIRH, évaluations, sondage).

Document technique complet (données, perfs, limites, protocole de mise à jour) :
[docs/model_card.md](docs/model_card.md).

## Stack technique

| Brique | Techno |
|---|---|
| API | FastAPI + Pydantic (doc Swagger/OpenAPI auto) |
| Modèle | scikit-learn (`Pipeline` sérialisé en `.joblib`) |
| Base de données | PostgreSQL via SQLAlchemy |
| Tests | Pytest + pytest-cov (couverture ≥ 90 % imposée) |
| CI/CD | GitHub Actions (tests) + déploiement Render sur tag |
| Hébergement | Render (Docker) + PostgreSQL managé Neon |
| Conteneurisation | Docker / docker-compose (dev local) |

## Architecture du dépôt

```
app/
├── main.py        FastAPI : endpoints (/health, /predict, /predict/batch, /predictions)
├── schemas.py     contrats Pydantic (validation d'entrée, réponses)
├── model.py       chargement de l'artefact + décision au seuil
├── db.py          connexion SQLAlchemy (URL depuis l'environnement)
├── orm.py         tables (employes, predictions) — mixin des 25 champs métier
├── crud.py        lecture/écriture en base
└── security.py    authentification par clé d'API (X-API-Key)
ml/
├── preprocessing.py  jointure des 3 sources + Pipeline (features + one-hot + RF)
├── train.py          entraîne, calcule le seuil, exporte model.joblib + metadata.json
└── metadata.json     seuil, métriques, versions
scripts/            create_db.py + load_dataset.py (init base, insertion du dataset)
tests/              50+ tests unitaires et fonctionnels (pytest)
data/raw/           les 3 CSV sources (SIRH, éval, sondage)
docs/               plan de mission, schéma DB, model card, guide de déploiement
Dockerfile · render.yaml · .github/workflows/ci.yml
```

## Installation (dev local)

```bash
# 1. Environnement (uv recommandé, cohérent avec le parcours)
uv sync                      # installe les dépendances + le groupe dev

# 2. Configuration
cp .env.example .env         # puis renseigner DATABASE_URL et API_KEY

# 3. Entraîner / régénérer l'artefact du modèle
python -m ml.train           # produit ml/model.joblib + ml/metadata.json

# 4. Base de données locale (PostgreSQL via Docker, port hôte 5433)
docker compose up -d
python -m scripts.create_db      # crée les tables (idempotent)
python -m scripts.load_dataset   # insère les 1470 employés du dataset
```

## Utilisation

```bash
# Lancer l'API en local
uvicorn app.main:app --reload
# Documentation interactive : http://localhost:8000/docs
```

Les endpoints de prédiction exigent l'en-tête `X-API-Key`. Exemple d'appel :

```bash
curl -X POST https://attrition-api-526p.onrender.com/predict \
  -H "X-API-Key: <votre_cle>" -H "Content-Type: application/json" \
  -d '{"age":41,"genre":"F","revenu_mensuel":5993, ... }'   # voir l'exemple du Swagger
# → {"probabilite_depart":0.70,"prediction":1,"seuil":0.415,"version_modele":"0.1.0"}
```

Dans le Swagger (`/docs`), le bouton **Authorize** permet de renseigner la clé une fois pour tous les
appels de test. Chaque appel à `POST /predict` ou `/predict/batch` est **tracé en base** (input +
prédiction + seuil + version + horodatage) et relisible via `GET /predictions`. Schéma de la base :
[docs/db_schema.md](docs/db_schema.md).

## Déploiement & sécurisation

- **Hébergement :** API conteneurisée (Docker) déployée sur **Render** ; base **PostgreSQL managée**
  (**Neon**) connectée via le secret `DATABASE_URL`. Infra décrite dans [render.yaml](render.yaml).
- **CI/CD :** GitHub Actions (tests + couverture à chaque push) ; le déploiement Render est déclenché
  par un **tag de version** (job `deploy`, environnement `production`).
- **Authentification :** endpoints de prédiction protégés par clé d'API (en-tête `X-API-Key`) ;
  `/health` reste public.
- **Secrets :** jamais dans le dépôt — `RENDER_DEPLOY_HOOK` dans l'environnement GitHub `production`,
  `DATABASE_URL` et `API_KEY` dans les variables du service Render.

Guide de déploiement pas à pas : [docs/deploiement.md](docs/deploiement.md).

## Contribuer

Conventions de branches, de commits et de versions : voir [CONTRIBUTING.md](CONTRIBUTING.md).
