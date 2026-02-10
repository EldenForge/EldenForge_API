from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core import datasets, filter_dataframe

router = APIRouter()


@router.get("/{item_id}")
def get_npc_by_id(item_id: str):
    """Récupère un NPC par son ID."""
    df = datasets.get("npcs")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="NPC non trouvé")
    return result.to_dict(orient="records")[0]


@router.get("")
def get_npcs(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    location: Optional[str] = Query(None, description="Filtrer par localisation")
):
    """Récupère les NPCs avec filtres optionnels."""
    df = datasets.get("npcs")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "location": location})
