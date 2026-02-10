from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core import datasets, filter_dataframe

router = APIRouter()


@router.get("/{item_id}")
def get_creature_by_id(item_id: str):
    """Récupère une créature par son ID."""
    df = datasets.get("creatures")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Créature non trouvée")
    return result.to_dict(orient="records")[0]


@router.get("")
def get_creatures(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    location: Optional[str] = Query(None, description="Filtrer par localisation")
):
    """Récupère les créatures avec filtres optionnels."""
    df = datasets.get("creatures")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "location": location})
