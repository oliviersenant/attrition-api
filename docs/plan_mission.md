# Plan d'attaque — Mission 4 : Déployez un modèle de Machine Learning

## Contexte

Futurisys (DT : Aurélien) veut rendre **opérationnel** le modèle d'attrition de la mission 3
(TechNova) via une API de production, testée, versionnée et déployée en CI/CD. C'est une mission
**d'ingénierie logicielle / MLOps**, pas de data science : le modèle existe déjà, l'enjeu est de le
**servir proprement**.

**Point de départ réel (constaté en explorant les deux missions) :**
- Le modèle est un **`RandomForestClassifier`** fine-tuné (`n_estimators=300, max_depth=8,
  min_samples_leaf=10, min_samples_split=5, max_features='log2', class_weight='balanced',
  random_state=42`), cible `a_quitte_l_entreprise` (Oui/Non → 1/0), **décision au seuil 0.417**
  (F-beta β=2), pas 0.5. Rappel classe « Oui » ≈ 0.73.
- **Aucun artefact sérialisé n'existe** : le modèle ne vit qu'en mémoire du notebook, et le
  preprocessing est **procédural** (`nettoyer_features`, `ajouter_features`, `encoder_qualitatives`
  via `pd.get_dummies`) — rien de réutilisable en l'état pour une API.
- Les données viennent de **3 CSV joints en `inner` sur `id_employee`** (clé harmonisée : SIRH a
  `id_employee` ; EVAL a `eval_number` = `"E_123"` → int ; SONDAGE a `code_sondage` → renommé).
- Le **vault ne couvre pas** la stack de cette mission (FastAPI, Pydantic, PostgreSQL, pytest, CI/CD,
  HF Spaces) : seuls les cours **Git/GitHub** y sont. Le travail s'appuiera sur mon expertise + les
  docs officielles citées au brief, en signalant ce qui n'est pas adossé au cours.

**Décisions actées avec Olivier :**
1. **Hébergement** : API (Docker) sur **Hugging Face Spaces** + **Postgres managé** (Neon ou
   Supabase, free tier) via secret `DATABASE_URL` ; dev local en `docker-compose` ; Postgres de test
   en service GitHub Actions.
2. **Modèle** : **refactor du code procédural en un vrai `Pipeline` sklearn** entraîné par un
   `train.py` qui exporte l'artefact `.joblib` + le seuil + les métadonnées.
3. **Méthode** : **étape par étape, guidé** — à chaque étape : intuition/mécanisme → validation
   d'Olivier → implémentation → **synthèse d'étape dans le vault** (skill `synthese-etape`).

**Résultat visé :** un POC de production complet — repo Git structuré, API FastAPI documentée
(Swagger), tests Pytest + couverture, base PostgreSQL traçant tous les échanges, pipeline CI/CD
GitHub Actions déployant sur HF Spaces.

---

## Architecture cible du dépôt

Nouveau dépôt Git dédié, initialisé dans le dossier de la mission 4 (qui ne contient aujourd'hui que
les 2 `.md` du brief + ce `docs/` ; le repo racine OpenClassRooms n'est **pas** un dépôt Git).

```
4-Déployez un modèle de Machine Learning/
├── README.md                  # présentation, install, usage, déploiement, auth/sécu
├── pyproject.toml             # (uv, cohérent mission 3) + requirements.txt exporté
├── Dockerfile                 # image API pour HF Spaces
├── docker-compose.yml         # dev local : api + postgres
├── .env.example               # DATABASE_URL, API_KEY... (jamais de secret réel)
├── .github/workflows/ci.yml   # tests + couverture + déploiement HF
├── app/                       # couche API
│   ├── main.py                #   FastAPI, endpoints, lifespan (chargement modèle)
│   ├── schemas.py             #   Pydantic (entrée employé + sortie prédiction)
│   ├── model.py               #   load pipeline + predict_proba + seuil
│   ├── db.py                  #   engine/session SQLAlchemy
│   ├── orm.py                 #   tables ORM (dataset, predictions)
│   ├── crud.py                #   lecture/écriture DB
│   └── security.py            #   auth par clé d'API (header)
├── ml/                        # couche modèle
│   ├── preprocessing.py       #   transformer réutilisable (jointure %/ratios/one-hot)
│   ├── train.py               #   entraîne le Pipeline, calcule le seuil, dump artefacts
│   ├── model.joblib           #   artefact versionné (ou via Git LFS / téléchargé au build)
│   └── metadata.json          #   seuil, features, métriques, version, date
├── data/raw/                  # les 3 CSV copiés depuis la mission 3
├── scripts/
│   ├── create_db.py           #   création base + tables (SQLAlchemy)
│   └── load_dataset.py        #   insertion du dataset complet en base
├── tests/                     # pytest (unitaires + fonctionnels)
│   ├── conftest.py            #   fixtures (client, DB de test)
│   ├── test_preprocessing.py
│   ├── test_model.py
│   ├── test_api.py
│   └── test_db.py
└── docs/
    ├── plan_mission.md        #   ce fichier
    ├── db_schema.md           #   modèle de données (UML/MCD)
    ├── model_card.md          #   doc technique du modèle + maintenance
    └── synthese_*.md          #   synthèses d'étape (renvoi vault)
```

---

## Déroulé étape par étape (les 6 étapes du brief)

> À chaque étape : d'abord le **pourquoi/mécanisme**, validation d'Olivier, puis implémentation, puis
> **synthèse d'étape** via le skill `synthese-etape` (Partie 1 Apprentissage / Partie 2 Soutenance),
> écrite dans `../obsidian/wiki/synthesis/`.

### Pré-étape (transverse) — Empaqueter le modèle *(le cœur technique, à faire tôt)*
Sans artefact servable, aucune étape API n'est possible. On construit un **`Pipeline` sklearn unique**
`brut → prédiction` :
- **`preprocessing.py`** — un transformer (custom `BaseEstimator/TransformerMixin` ou
  `FunctionTransformer` sur DataFrame) qui rejoue la logique du notebook : conversion
  `augementation_salaire_precedente` `"11 %"`→float, création des **4 features**
  (`satisfaction_moyenne`, `ratio_stagnation_promo`, `ratio_anciennete_poste`, `revenu_par_annee_exp`),
  puis **`ColumnTransformer` + `OneHotEncoder(handle_unknown='ignore')`** sur les 7 catégorielles
  (`genre, statut_marital, departement, poste, heure_supplementaires, domaine_etude,
  frequence_deplacement`). *Pourquoi `OneHotEncoder` et non `get_dummies` : il **mémorise les
  modalités** au `fit` et absorbe une catégorie inconnue en prod — c'est ce qui rend l'inférence
  robuste, là où `get_dummies`+reindex casse dès qu'une modalité manque.*
- **`train.py`** — charge/joint les 3 CSV, sépare `X`/`y`, `train_test_split` stratifié, `fit` du
  Pipeline (RF avec les hyperparamètres figés), **recalcule le seuil optimal** (courbe P-R, F2) pour
  reproductibilité (doit retomber ≈ 0.417), `joblib.dump(pipeline)` + `metadata.json` (seuil,
  métriques, version). *La logique de décision au seuil vit côté API, pas dans le Pipeline* (le RF
  fournit `predict_proba`, l'API applique 0.417).

### Étape 1 — Gestion de version & collaboration (Git)  *(seul volet couvert par le vault)*
- `git init` dans le dossier mission 4, `.gitignore` (venv, `.env`, artefacts lourds), structure de
  dossiers ci-dessus (pas tout à la racine), **README** initial.
- **Conventions** : branches par fonctionnalité (`feat/api`, `feat/db`, `feat/ci`…), commits
  descriptifs, **tags de version** (`v0.1.0`…). Créer le remote GitHub.
- S'appuie directement sur les cours vault `Gérez du code avec Git` et `Devenez un expert de Git`
  (GitFlow, branches, remotes, résolution de conflits).

### Étape 2 — CI/CD (GitHub Actions + HF Spaces)
- `ci.yml` : job **test** (lint + `pytest --cov`) sur push/PR, avec **service Postgres** conteneurisé
  pour les tests DB ; **protection de branche** `main` (merge conditionné aux tests verts) ; job
  **deploy** vers HF Spaces sur tag/`main`.
- **Gestion des secrets** (GitHub Secrets → HF Spaces secrets) : `DATABASE_URL`, `HF_TOKEN`, `API_KEY`.
- **Environnements** dev/test/prod (variables + secrets par environnement). Vigilance brief : garder
  le pipeline **< 10 min**.

### Étape 3 — Développement de l'API (FastAPI + Pydantic)
- **Schémas Pydantic** : `EmployeeFeatures` (tous les champs bruts d'un employé — union
  SIRH+EVAL+SONDAGE hors id/target — typés et validés : bornes d'`age`, enums `genre` F/M,
  `heure_supplementaires` Oui/Non, etc.) ; `PredictionResponse` (probabilité, décision 0/1, seuil,
  version modèle).
- **Endpoints** : `GET /health` ; `POST /predict` (un employé → proba + décision au seuil 0.417, +
  écriture DB) ; option `POST /predict/batch` ; `GET /predictions` (relecture des prédictions loggées).
- Chargement du Pipeline au démarrage (`lifespan`). **Swagger/OpenAPI** auto-généré. Gestion propre
  des erreurs de validation (422) et cas limites.

### Étape 4 — Dataset & PostgreSQL (SQLAlchemy)
- **Modèle de données** (schéma UML dans `docs/db_schema.md`) : table **dataset** (les employés +
  leur label réel) et table **predictions** (snapshot d'entrée + proba + décision + seuil + horodatage
  + version modèle). *Toute interaction modèle passe par la DB* (exigence brief : traçabilité).
- `create_db.py` (création base + tables via ORM) ; `load_dataset.py` (insertion du dataset complet).
- L'endpoint `/predict` **écrit systématiquement** input+output en base (via `crud.py`).

### Étape 5 — Tests unitaires & fonctionnels (Pytest + pytest-cov)
- **Unitaires** : `preprocessing` (conversion `%`, calcul des 4 ratios, one-hot sur modalité
  inconnue), logique de seuil, validation Pydantic (cas valides/invalides).
- **Fonctionnels** : `TestClient` sur les endpoints (200/422/erreurs), interaction DB (fixture base de
  test), scénarios d'erreur. **Rapport de couverture** `pytest-cov`. Reproductibilité (seed figée).

### Étape 6 — Documentation
- **README** complet (install, usage, déploiement, **authentification & sécurisation**), **doc API**
  (Swagger + exemples d'appels), **model card** (perfs, limites, protocole de mise à jour), **schéma
  DB**. Justifier les choix techniques.

---

## Vérification (end-to-end)

1. **Modèle** : `python ml/train.py` → produit `model.joblib` + `metadata.json` ; vérifier que le
   seuil recalculé ≈ 0.417 et le rappel classe « Oui » ≈ 0.73 (cohérent notebook).
2. **API locale** : `docker-compose up` (api + postgres) → `GET /health` OK ; `POST /predict` avec un
   employé de test renvoie une proba plausible et **écrit une ligne** dans la table `predictions`
   (vérif SQL). Swagger accessible sur `/docs`.
3. **DB** : `create_db.py` puis `load_dataset.py` → le dataset complet est inséré ; requête de
   relecture OK.
4. **Tests** : `pytest --cov` vert en local, rapport de couverture généré.
5. **CI/CD** : un push sur une branche déclenche les tests (Postgres service) ; un merge sur `main` /
   un tag déclenche le déploiement HF Spaces ; l'API déployée répond sur son URL publique et logge en
   Postgres managé.

## Points de vigilance

- **Alignement train/inférence** : la robustesse repose sur le `OneHotEncoder` mémorisé — à tester
  explicitement (modalité inconnue en entrée).
- **Seuil 0.417 côté API**, jamais 0.5 — sinon on casse la logique métier (rappel des partants).
- **Secrets** : jamais de `DATABASE_URL`/token en clair dans le repo (`.env.example` seulement).
- **Tension Postgres/HF Spaces** déjà tranchée (Postgres managé + secret) — à documenter dans le README.
- **Poids de l'artefact** `model.joblib` : décider Git LFS vs (re)génération au build pour ne pas
  alourdir le repo.
