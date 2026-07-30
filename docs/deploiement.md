# Guide de déploiement — Hugging Face Spaces + Postgres managé

Ce guide décrit la mise en production de l'API. L'infrastructure applicative (Dockerfile, workflow de
déploiement, authentification) est déjà dans le dépôt ; il reste à **créer les comptes externes** et
à **poser les secrets**. Architecture cible :

```
GitHub (push tag v*) ──CI verte──> job deploy ──git push──> HF Space (build Docker) ──> API live
                                                                    │  DATABASE_URL (secret)
                                                                    ▼
                                              PostgreSQL managé (Neon / Supabase, free tier)
```

## 1. Base de données managée (Neon — gratuit)

1. Créer un compte sur [neon.tech](https://neon.tech) → nouveau projet, région Europe.
2. Récupérer la **connection string**. La convertir au format attendu par l'app (driver `psycopg`) :
   ```
   postgresql+psycopg://<user>:<password>@<host>/<db>?sslmode=require
   ```
   (Neon fournit `postgresql://…` : ajouter `+psycopg` après `postgresql` et garder `sslmode=require`.)
3. **Créer les tables + charger le dataset** dans cette base, une fois, depuis ta machine :
   ```bash
   export DATABASE_URL="postgresql+psycopg://…?sslmode=require"   # l'URL Neon
   uv run python -m scripts.create_db
   uv run python -m scripts.load_dataset      # 1470 employés
   ```

## 2. Hugging Face Space

1. Créer un compte sur [huggingface.co](https://huggingface.co).
2. **New Space** → nom `attrition-api`, **SDK = Docker**, template **Blank**, visibilité au choix.
3. Dans le Space → **Settings → Variables and secrets**, ajouter deux **secrets** :
   - `DATABASE_URL` = l'URL Neon (avec `+psycopg` et `sslmode=require`) ;
   - `API_KEY` = une clé forte de ton choix (celle à envoyer dans l'en-tête `X-API-Key`).
4. Créer un **token d'accès** : profil → **Settings → Access Tokens** → nouveau token **write**
   (servira à GitHub pour pousser vers le Space). Le copier.

## 3. GitHub — secrets & variables du déploiement

Dans le dépôt `attrition-api` → **Settings** :

1. **Environments** → **New environment** nommé `production` → dans ses **secrets**, ajouter
   `HF_TOKEN` = le token write HF de l'étape 2.4.
2. **Secrets and variables → Actions → Variables** (onglet *Variables*), ajouter :
   - `HF_USERNAME` = ton identifiant Hugging Face ;
   - `HF_SPACE` = `attrition-api`.

## 4. Déclencher le déploiement

Le job `deploy` ne se lance que sur un **tag de version**, après une CI verte :

```bash
git switch main && git pull
git tag -a v0.6.0 -m "Premier deploiement HF Spaces"
git push origin v0.6.0
```

Suivre l'exécution dans l'onglet **Actions** (job « Déploiement Hugging Face Spaces »), puis le build
du Space côté HF (onglet **Logs** du Space). Une fois « Running » :

```bash
# health (public)
curl https://<user>-attrition-api.hf.space/health

# prédiction (clé requise)
curl -X POST https://<user>-attrition-api.hf.space/predict \
  -H "X-API-Key: <ta_cle>" -H "Content-Type: application/json" \
  -d @exemple_employe.json
```

Documentation interactive : `https://<user>-attrition-api.hf.space/docs`.

## Notes

- **Secrets** : jamais dans le dépôt. `HF_TOKEN` vit dans l'environnement GitHub `production` ;
  `DATABASE_URL` et `API_KEY` dans les secrets du Space. Le `.env` local n'est pas versionné.
- **Environnements** : `production` (GitHub) permet, si besoin, d'exiger une **validation manuelle**
  avant déploiement (Settings de l'environnement → *Required reviewers*).
- **Le modèle n'est pas déployé en binaire** : le Dockerfile le **ré-entraîne au build** à partir des
  CSV du dépôt (décision « régénération plutôt que Git LFS »).
