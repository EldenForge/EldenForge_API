from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from core import datasets, filter_dataframe
from core.upgrades import upgrades_for

router = APIRouter()


@router.get("/{item_id}")
def get_weapon_by_id(item_id: str):
    """Récupère une arme par son ID."""
    df = datasets.get("weapons")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Arme non trouvée")
    return result.to_dict(orient="records")[0]


@router.get("/{item_id}/upgrades")
def get_weapon_upgrades(item_id: str):
    """Renvoie les lignes d'upgrades (Standard +0..+25) pour une arme."""
    df = datasets.get("weapons")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Arme non trouvée")
    name = str(result.iloc[0]["name"])
    return upgrades_for(name, kind="weapon")


@router.get("")
def get_weapons(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie")
):
    """Récupère les armes avec filtres optionnels."""
    df = datasets.get("weapons")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "category": category})
