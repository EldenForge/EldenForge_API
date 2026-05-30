from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core import datasets, filter_dataframe
from core.upgrades import upgrades_for

router = APIRouter()


@router.get("/{item_id}")
def get_shield_by_id(item_id: str):
    """Récupère un bouclier par son ID."""
    df = datasets.get("shields")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Bouclier non trouvé")
    return result.to_dict(orient="records")[0]


@router.get("/{item_id}/upgrades")
def get_shield_upgrades(item_id: str):
    """Renvoie les lignes d'upgrades (Standard +0..+25) pour un bouclier."""
    df = datasets.get("shields")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Bouclier non trouvé")
    name = str(result.iloc[0]["name"])
    return upgrades_for(name, kind="shield")


@router.get("")
def get_shields(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie")
):
    """Récupère les boucliers avec filtres optionnels."""
    df = datasets.get("shields")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "category": category})
