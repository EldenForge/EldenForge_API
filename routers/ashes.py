from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core import datasets, filter_dataframe

router = APIRouter()


@router.get("/{item_id}")
def get_ash_by_id(item_id: str):
    """Récupère une cendre de guerre par son ID."""
    df = datasets.get("ashes")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Cendre non trouvée")
    return result.to_dict(orient="records")[0]


@router.get("")
def get_ashes(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    affinity: Optional[str] = Query(None, description="Filtrer par affinité"),
    skill: Optional[str] = Query(None, description="Filtrer par compétence")
):
    """Récupère les cendres de guerre avec filtres optionnels."""
    df = datasets.get("ashes")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "affinity": affinity, "skill": skill})
