# Attrition API — Déploiement du modèle de prédiction d'attrition (Futurisys)

API de production exposant le modèle de **prédiction d'attrition des employés** développé pour
TechNova (mission précédente). Le client Futurisys veut rendre ce modèle **opérationnel** : une API
performante, testée, versionnée, traçant tous ses échanges en base de données, et déployée en CI/CD.

> **Statut :** 🚧 POC en construction — mission guidée OpenClassrooms (parcours AI/ML Engineer).

## Le modèle exposé

- **Tâche :** classification binaire — un employé va-t-il quitter l'entreprise ? (`a_quitte_l_entreprise`)
- **Algorithme :** `RandomForestClassifier` (scikit-learn) fine-tuné, `class_weight='balanced'`.
- **Décision :** prise au **seuil 0.417** (optimisé F-beta β=2, priorité au rappel), **pas 0.5** —
  mieux vaut une fausse alerte qu'un départ raté.
- **Performance :** rappel de la classe « part » ≈ 0.73 (≈ 7 partants détectés sur 10).
- **Entrées :** caractéristiques d'un employé issues de 3 sources (SIRH, évaluations, sondage).

## Stack technique

| Brique | Techno |
|---|---|
| API | FastAPI + Pydantic (doc Swagger/OpenAPI auto) |
| Modèle | scikit-learn (`Pipeline` sérialisé en `.joblib`) |
| Base de données | PostgreSQL via SQLAlchemy |
| Tests | Pytest + pytest-cov |
| CI/CD | GitHub Actions → Hugging Face Spaces |
| Conteneurisation | Docker / docker-compose (dev local) |

## Architecture du dépôt

```
app/        couche API (FastAPI, schémas Pydantic, accès DB, sécurité)
ml/         couche modèle (preprocessing, train.py, metadata)
scripts/    création de la base + chargement du dataset
tests/      tests unitaires et fonctionnels (pytest)
data/raw/   les 3 CSV sources (SIRH, éval, sondage)
docs/       plan de mission, schéma DB, model card, synthèses d'étape
```

## Installation (dev local)

```bash
# 1. Environnement (uv recommandé, cohérent avec le parcours)
uv sync                      # installe les dépendances + le groupe dev

# 2. Configuration
cp .env.example .env         # puis renseigner DATABASE_URL et API_KEY

# 3. Entraîner / régénérer l'artefact du modèle
python ml/train.py           # produit ml/model.joblib + ml/metadata.json
```

## Utilisation (à venir)

```bash
# Lancer l'API en local
uvicorn app.main:app --reload
# Documentation interactive : http://localhost:8000/docs
```

## Déploiement & sécurisation

- **Hébergement :** API conteneurisée sur **Hugging Face Spaces** ; base **PostgreSQL managée**
  (Neon/Supabase) connectée via le secret `DATABASE_URL`.
- **Authentification :** endpoints protégés par clé d'API (en-tête `X-API-Key`).
- **Secrets :** jamais dans le dépôt — gérés via GitHub Secrets / secrets HF Spaces.

*(Sections install/usage/déploiement détaillées complétées au fil des étapes — voir
[docs/plan_mission.md](docs/plan_mission.md).)*

## Contribuer

Conventions de branches, de commits et de versions : voir [CONTRIBUTING.md](CONTRIBUTING.md).
