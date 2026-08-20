# Guide de déploiement — Render + Postgres managé (Neon)

Ce guide décrit la mise en production de l'API. L'infrastructure applicative (Dockerfile,
`render.yaml`, workflow de déploiement, authentification) est déjà dans le dépôt ; il reste à **créer
les comptes externes** et à **poser les secrets**. Architecture cible :

```
GitHub (push tag v*) ──CI verte──> job deploy ──deploy hook──> Render (build Docker) ──> API live
                                                                     │  DATABASE_URL (var Render)
                                                                     ▼
                                              PostgreSQL managé (Neon, free tier)
```

> **Pourquoi Render et pas Hugging Face Spaces ?** Depuis juillet 2026, HF a rendu les *Docker
> Spaces* payants pour les comptes gratuits. Le brief autorisant « HF Spaces **ou équivalent** », on
> déploie sur Render (Docker natif, free tier). Rien de l'architecture ne change : le Dockerfile,
> l'auth et la base Neon sont host-agnostiques.

## 1. Base de données managée (Neon) — ✅ déjà fait

La base est créée, les tables et les 1470 employés sont chargés. `DATABASE_URL` (format `psycopg`) :
```
postgresql+psycopg://<user>:<password>@<host>/<db>?sslmode=require
```
(Pour recharger si besoin : `export DATABASE_URL=…` puis `uv run python -m scripts.create_db` et
`uv run python -m scripts.load_dataset`.)

## 2. Service web Render

1. Créer un compte sur [render.com](https://render.com) (connexion via GitHub recommandée).
2. **New → Web Service** → connecter le dépôt GitHub `attrition-api`.
   - Render détecte le `Dockerfile` (et le `render.yaml`). Runtime **Docker**, plan **Free**,
     région **Frankfurt**.
   - **Auto-Deploy : No** (le déploiement sera piloté par tag via GitHub Actions).
3. **Environment → Environment Variables**, ajouter :
   - `DATABASE_URL` = l'URL Neon. L'URL brute de Neon (`postgresql://…?sslmode=require`) suffit :
     l'app force le driver psycopg v3 automatiquement (`app/db.py:normaliser_url`).
   - `API_KEY` = une clé forte de ton choix (l'en-tête `X-API-Key` pour appeler l'API).
   - *(Render fournit `PORT` automatiquement — ne pas le définir.)*
4. **Settings → Deploy Hook** : copier l'URL du **deploy hook** (elle sert à GitHub pour déclencher
   le déploiement).

## 3. GitHub — secret du déploiement

Dépôt `attrition-api` → **Settings → Environments → New environment** nommé `production` → dans ses
**secrets**, ajouter :
- `RENDER_DEPLOY_HOOK` = l'URL du deploy hook copiée à l'étape 2.4.

## 4. Déclencher le déploiement

Le job `deploy` ne se lance que sur un **tag de version**, après une CI verte :

```bash
git switch main && git pull
git tag -a v0.6.0 -m "Premier deploiement Render"
git push origin v0.6.0
```

Suivre l'exécution dans **Actions** (job « Déploiement Render »), puis le build dans le dashboard
Render (onglet **Logs**). Une fois « Live » :

```bash
# health (public)
curl https://attrition-api.onrender.com/health

# prédiction (clé requise)
curl -X POST https://attrition-api.onrender.com/predict \
  -H "X-API-Key: <ta_cle>" -H "Content-Type: application/json" \
  -d '{ … un employé … }'
```

Documentation interactive : `https://attrition-api.onrender.com/docs`
(l'URL exacte est affichée en haut du service dans le dashboard Render).

## Notes

- **Cold start** : le free tier Render met le service en veille après 15 min d'inactivité ; le
  premier appel suivant prend 30-60 s (le temps de réveiller le conteneur). Sans conséquence
  fonctionnelle ; pour une démo, faire un appel « à blanc » 1 min avant.
- **Le modèle n'est pas déployé en binaire** : le Dockerfile le **ré-entraîne au build** à partir des
  CSV du dépôt (décision « régénération plutôt que Git LFS »).
- **Secrets** : jamais dans le dépôt. `RENDER_DEPLOY_HOOK` dans l'environnement GitHub `production` ;
  `DATABASE_URL` et `API_KEY` dans les variables du service Render.
- **Environnements** : l'environnement GitHub `production` permet, si besoin, d'exiger une
  **validation manuelle** avant déploiement (Settings de l'environnement → *Required reviewers*).
