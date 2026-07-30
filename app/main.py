"""API Attrition — expose le modèle de prédiction d'attrition de Futurisys.

Documentation interactive (Swagger/OpenAPI) : `/docs` — générée depuis les
contrats Pydantic de `app/schemas.py` : la doc et la validation sont le même
objet, elles ne peuvent pas diverger.

Traçabilité (exigence Futurisys) : chaque prédiction est enregistrée en base
(input reçu + output rendu + version/seuil/horodatage). Si la base est
indisponible, la prédiction ÉCHOUE (500) : une prédiction non tracée
violerait le contrat d'audit — on préfère refuser que prédire en silence.
"""

from contextlib import asynccontextmanager
from typing import Annotated

import pandas as pd
from fastapi import Depends, FastAPI, Query, Request
from pydantic import Field
from sqlalchemy.orm import Session

from app import crud
from app.db import obtenir_session
from app.model import ModeleAttrition
from app.schemas import (
    EmployeeFeatures,
    HealthResponse,
    PredictionRecord,
    PredictionResponse,
)

DESCRIPTION = """
Prédit le risque de départ d'un employé (classification binaire, RandomForest).

La décision est prise au **seuil métier 0.415** (optimisé F-beta β=2, priorité
au rappel : mieux vaut une fausse alerte qu'un départ raté), pas à 0.5.

Chaque échange avec le modèle est **tracé en base PostgreSQL** (audit,
suivi de dérive) et relisible via `GET /predictions`.
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
    version="0.4.0",
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
def predict(
    employe: EmployeeFeatures,
    request: Request,
    session: Annotated[Session, Depends(obtenir_session)],
) -> dict:
    """Prédit le risque de départ d'un employé (échange tracé en base).

    Toute donnée non conforme au schéma (champ manquant, borne violée,
    modalité inconnue) est rejetée en 422 avant d'atteindre le modèle.
    """
    modele: ModeleAttrition = request.app.state.modele
    entree = employe.model_dump()
    resultat = modele.predire(pd.DataFrame([entree]))[0]
    crud.enregistrer_predictions(session, [entree], [resultat])
    return resultat


@app.post("/predict/batch", response_model=list[PredictionResponse], tags=["prediction"])
def predict_batch(
    employes: Annotated[list[EmployeeFeatures], Field(min_length=1, max_length=1000)],
    request: Request,
    session: Annotated[Session, Depends(obtenir_session)],
) -> list[dict]:
    """Prédit le risque de départ pour une liste d'employés (scoring d'effectif)."""
    modele: ModeleAttrition = request.app.state.modele
    entrees = [employe.model_dump() for employe in employes]
    resultats = modele.predire(pd.DataFrame(entrees))
    crud.enregistrer_predictions(session, entrees, resultats)
    return resultats


@app.get("/predictions", response_model=list[PredictionRecord], tags=["monitoring"])
def predictions(
    session: Annotated[Session, Depends(obtenir_session)],
    limite: Annotated[int, Query(ge=1, le=500, description="Nb max de lignes")] = 50,
) -> list[PredictionRecord]:
    """Relit les derniers échanges tracés (audit) — les plus récents d'abord."""
    return crud.lister_predictions(session, limite=limite)
