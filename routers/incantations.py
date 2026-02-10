from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core import datasets, filter_dataframe

router = APIRouter()


@router.get("/{item_id}")
def get_incantation_by_id(item_id: str):
    """Récupère une incantation par son ID."""
    df = datasets.get("incantations")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Incantation non trouvée")
    return result.to_dict(orient="records")[0]


@router.get("")
def get_incantations(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    type: Optional[str] = Query(None, description="Filtrer par type")
):
    """Récupère les incantations avec filtres optionnels."""
    df = datasets.get("incantations")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "type": type})
