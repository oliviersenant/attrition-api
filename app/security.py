"""Authentification de l'API par clé (en-tête HTTP `X-API-Key`).

Une fois l'API publique (déployée sur HF Spaces), n'importe qui peut appeler
les endpoints. Une clé partagée est la protection minimale attendue : elle
n'identifie pas *qui* appelle (ce n'est pas de l'OAuth), mais elle **restreint
l'accès** aux détenteurs de la clé, ce qui suffit pour un POC interne.

La clé attendue vient de la configuration (`API_KEY`, injectée par secret en
prod). La comparaison utilise `secrets.compare_digest` : temps constant, pour
ne pas fuiter d'information via la durée de la comparaison (timing attack).
"""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.db import Reglages

# Déclaré comme *security scheme* OpenAPI : fait apparaître le bouton « Authorize »
# dans Swagger. auto_error=False → on renvoie notre propre 401 (message explicite).
cle_api_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verifier_cle_api(cle: str | None = Depends(cle_api_header)) -> None:
    """Dépendance FastAPI : rejette (401) toute requête sans clé valide."""
    attendue = Reglages().api_key
    if cle is None or not secrets.compare_digest(cle, attendue):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé d'API invalide ou absente (en-tête X-API-Key).",
        )
