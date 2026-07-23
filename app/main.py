"""API Attrition — expose le modèle de prédiction d'attrition de Futurisys.

Documentation interactive (Swagger/OpenAPI) : `/docs` — générée depuis les
contrats Pydantic de `app/schemas.py` : la doc et la validation sont le même
objet, elles ne peuvent pas diverger.
"""

from contextlib import asynccontextmanager
from typing import Annotated

import pandas as pd
from fastapi import FastAPI, Request
from pydantic import Field

from app.model import ModeleAttrition
from app.schemas import EmployeeFeatures, HealthResponse, PredictionResponse

DESCRIPTION = """
Prédit le risque de départ d'un employé (classification binaire, RandomForest).

La décision est prise au **seuil métier 0.415** (optimisé F-beta β=2, priorité
au rappel : mieux vaut une fausse alerte qu'un départ raté), pas à 0.5.
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Chargé UNE fois au démarrage (pas à chaque requête) : l'artefact est
    # immuable pendant la vie du process, le désérialiser par appel serait
    # un contresens de performance.
    app.state.modele = ModeleAttrition.charger()
    yield


app = FastAPI(
    title="Attrition API — Futurisys",
    version="0.3.0",
    description=DESCRIPTION,
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
def health(request: Request) -> dict:
    """Vérifie que l'API répond et que le modèle est chargé."""
    modele: ModeleAttrition = request.app.state.modele
    return {
        "status": "ok",
        "version_modele": modele.version,
        "seuil": modele.seuil,
        "date_entrainement": modele.date_entrainement,
    }


@app.post("/predict", response_model=PredictionResponse, tags=["prediction"])
def predict(employe: EmployeeFeatures, request: Request) -> dict:
    """Prédit le risque de départ d'un employé.

    Toute donnée non conforme au schéma (champ manquant, borne violée,
    modalité inconnue) est rejetée en 422 avant d'atteindre le modèle.
    """
    modele: ModeleAttrition = request.app.state.modele
    entree = pd.DataFrame([employe.model_dump()])
    resultat = modele.predire(entree)[0]
    # TODO (étape 4 — PostgreSQL) : enregistrer ici l'input et l'output en
    # base afin de tracer chaque échange avec le modèle.
    return resultat


@app.post("/predict/batch", response_model=list[PredictionResponse], tags=["prediction"])
def predict_batch(
    employes: Annotated[list[EmployeeFeatures], Field(min_length=1, max_length=1000)],
    request: Request,
) -> list[dict]:
    """Prédit le risque de départ pour une liste d'employés (scoring d'effectif)."""
    modele: ModeleAttrition = request.app.state.modele
    entree = pd.DataFrame([employe.model_dump() for employe in employes])
    resultats = modele.predire(entree)
    # TODO (étape 4 — PostgreSQL) : tracer les échanges en base ici aussi.
    return resultats
