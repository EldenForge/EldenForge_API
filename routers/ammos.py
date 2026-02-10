from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core import datasets, filter_dataframe

router = APIRouter()


@router.get("/{item_id}")
def get_ammo_by_id(item_id: str):
    """Récupère une munition par son ID."""
    df = datasets.get("ammos")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Munition non trouvée")
    return result.to_dict(orient="records")[0]


@router.get("")
def get_ammos(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    type: Optional[str] = Query(None, description="Filtrer par type"),
    passive: Optional[str] = Query(None, description="Filtrer par effet passif")
):
    """Récupère les munitions avec filtres optionnels."""
    df = datasets.get("ammos")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "type": type, "passive": passive})
