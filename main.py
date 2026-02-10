from fastapi import FastAPI, HTTPException, Query, Request
from typing import Optional
import pandas as pd
import os
import logging
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Elden Ring API",
    description="API pour accéder aux données du dataset Elden Ring",
    version="1.0.0"
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware pour logger toutes les requêtes."""
    start_time = time.time()
    logger.info(f"Requête entrante: {request.method} {request.url.path}")

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(f"Requête terminée: {request.method} {request.url.path} - Status: {response.status_code} - Durée: {process_time:.3f}s")

    return response

DATASET_PATH = os.path.join(os.path.dirname(__file__), "Dataset")

# Chargement des données CSV
datasets = {}
csv_files = [
    "ammos", "armors", "ashes", "bosses", "classes", "creatures",
    "incantations", "items", "locations", "npcs", "shields",
    "sorceries", "spirits", "talismans", "weapons"
]

logger.info("Chargement des datasets...")
for csv_name in csv_files:
    file_path = os.path.join(DATASET_PATH, f"{csv_name}.csv")
    if os.path.exists(file_path):
        datasets[csv_name] = pd.read_csv(file_path)
        logger.info(f"Dataset '{csv_name}' chargé: {len(datasets[csv_name])} entrées")
    else:
        logger.warning(f"Dataset '{csv_name}' non trouvé: {file_path}")
logger.info(f"Chargement terminé: {len(datasets)} datasets chargés")


def filter_dataframe(df: pd.DataFrame, filters: dict) -> list:
    """Filtre un DataFrame selon les paramètres fournis."""
    result = df.copy()
    active_filters = {k: v for k, v in filters.items() if v is not None}
    if active_filters:
        logger.debug(f"Filtres appliqués: {active_filters}")
    for key, value in filters.items():
        if value is not None and key in result.columns:
            result = result[result[key].astype(str).str.contains(str(value), case=False, na=False)]
    logger.debug(f"Résultats après filtrage: {len(result)} entrées")
    return result.to_dict(orient="records")


# ==================== AMMOS ====================
@app.get("/ammos/{item_id}", tags=["Ammos"])
def get_ammo_by_id(item_id: str):
    """Récupère une munition par son ID."""
    df = datasets.get("ammos")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Munition non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/ammos", tags=["Ammos"])
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


# ==================== ARMORS ====================
@app.get("/armors/{item_id}", tags=["Armors"])
def get_armor_by_id(item_id: str):
    """Récupère une armure par son ID."""
    df = datasets.get("armors")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Armure non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/armors", tags=["Armors"])
def get_armors(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie")
):
    """Récupère les armures avec filtres optionnels."""
    df = datasets.get("armors")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "category": category})


# ==================== ASHES ====================
@app.get("/ashes/{item_id}", tags=["Ashes"])
def get_ash_by_id(item_id: str):
    """Récupère une cendre de guerre par son ID."""
    df = datasets.get("ashes")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Cendre non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/ashes", tags=["Ashes"])
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


# ==================== BOSSES ====================
@app.get("/bosses/{item_id}", tags=["Bosses"])
def get_boss_by_id(item_id: str):
    """Récupère un boss par son ID."""
    df = datasets.get("bosses")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Boss non trouvé")
    return result.to_dict(orient="records")[0]


@app.get("/bosses", tags=["Bosses"])
def get_bosses(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    region: Optional[str] = Query(None, description="Filtrer par région"),
    location: Optional[str] = Query(None, description="Filtrer par localisation")
):
    """Récupère les boss avec filtres optionnels."""
    df = datasets.get("bosses")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "region": region, "location": location})


# ==================== CLASSES ====================
@app.get("/classes/{item_id}", tags=["Classes"])
def get_class_by_id(item_id: str):
    """Récupère une classe par son ID."""
    df = datasets.get("classes")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Classe non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/classes", tags=["Classes"])
def get_classes(
    name: Optional[str] = Query(None, description="Filtrer par nom")
):
    """Récupère les classes avec filtres optionnels."""
    df = datasets.get("classes")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name})


# ==================== CREATURES ====================
@app.get("/creatures/{item_id}", tags=["Creatures"])
def get_creature_by_id(item_id: str):
    """Récupère une créature par son ID."""
    df = datasets.get("creatures")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Créature non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/creatures", tags=["Creatures"])
def get_creatures(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    location: Optional[str] = Query(None, description="Filtrer par localisation")
):
    """Récupère les créatures avec filtres optionnels."""
    df = datasets.get("creatures")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "location": location})


# ==================== INCANTATIONS ====================
@app.get("/incantations/{item_id}", tags=["Incantations"])
def get_incantation_by_id(item_id: str):
    """Récupère une incantation par son ID."""
    df = datasets.get("incantations")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Incantation non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/incantations", tags=["Incantations"])
def get_incantations(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    type: Optional[str] = Query(None, description="Filtrer par type")
):
    """Récupère les incantations avec filtres optionnels."""
    df = datasets.get("incantations")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "type": type})


# ==================== ITEMS ====================
@app.get("/items/{item_id}", tags=["Items"])
def get_item_by_id(item_id: str):
    """Récupère un item par son ID."""
    df = datasets.get("items")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Item non trouvé")
    return result.to_dict(orient="records")[0]


@app.get("/items", tags=["Items"])
def get_items(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    type: Optional[str] = Query(None, description="Filtrer par type")
):
    """Récupère les items avec filtres optionnels."""
    df = datasets.get("items")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "type": type})


# ==================== LOCATIONS ====================
@app.get("/locations/{item_id}", tags=["Locations"])
def get_location_by_id(item_id: str):
    """Récupère une localisation par son ID."""
    df = datasets.get("locations")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Localisation non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/locations", tags=["Locations"])
def get_locations(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    region: Optional[str] = Query(None, description="Filtrer par région")
):
    """Récupère les localisations avec filtres optionnels."""
    df = datasets.get("locations")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "region": region})


# ==================== NPCS ====================
@app.get("/npcs/{item_id}", tags=["NPCs"])
def get_npc_by_id(item_id: str):
    """Récupère un NPC par son ID."""
    df = datasets.get("npcs")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="NPC non trouvé")
    return result.to_dict(orient="records")[0]


@app.get("/npcs", tags=["NPCs"])
def get_npcs(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    location: Optional[str] = Query(None, description="Filtrer par localisation")
):
    """Récupère les NPCs avec filtres optionnels."""
    df = datasets.get("npcs")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "location": location})


# ==================== SHIELDS ====================
@app.get("/shields/{item_id}", tags=["Shields"])
def get_shield_by_id(item_id: str):
    """Récupère un bouclier par son ID."""
    df = datasets.get("shields")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Bouclier non trouvé")
    return result.to_dict(orient="records")[0]


@app.get("/shields", tags=["Shields"])
def get_shields(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie")
):
    """Récupère les boucliers avec filtres optionnels."""
    df = datasets.get("shields")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "category": category})


# ==================== SORCERIES ====================
@app.get("/sorceries/{item_id}", tags=["Sorceries"])
def get_sorcery_by_id(item_id: str):
    """Récupère une sorcellerie par son ID."""
    df = datasets.get("sorceries")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Sorcellerie non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/sorceries", tags=["Sorceries"])
def get_sorceries(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    type: Optional[str] = Query(None, description="Filtrer par type")
):
    """Récupère les sorcelleries avec filtres optionnels."""
    df = datasets.get("sorceries")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "type": type})


# ==================== SPIRITS ====================
@app.get("/spirits/{item_id}", tags=["Spirits"])
def get_spirit_by_id(item_id: str):
    """Récupère un esprit par son ID."""
    df = datasets.get("spirits")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Esprit non trouvé")
    return result.to_dict(orient="records")[0]


@app.get("/spirits", tags=["Spirits"])
def get_spirits(
    name: Optional[str] = Query(None, description="Filtrer par nom")
):
    """Récupère les esprits avec filtres optionnels."""
    df = datasets.get("spirits")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name})


# ==================== TALISMANS ====================
@app.get("/talismans/{item_id}", tags=["Talismans"])
def get_talisman_by_id(item_id: str):
    """Récupère un talisman par son ID."""
    df = datasets.get("talismans")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Talisman non trouvé")
    return result.to_dict(orient="records")[0]


@app.get("/talismans", tags=["Talismans"])
def get_talismans(
    name: Optional[str] = Query(None, description="Filtrer par nom")
):
    """Récupère les talismans avec filtres optionnels."""
    df = datasets.get("talismans")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name})


# ==================== WEAPONS ====================
@app.get("/weapons/{item_id}", tags=["Weapons"])
def get_weapon_by_id(item_id: str):
    """Récupère une arme par son ID."""
    df = datasets.get("weapons")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    result = df[df["id"] == item_id]
    if result.empty:
        raise HTTPException(status_code=404, detail="Arme non trouvée")
    return result.to_dict(orient="records")[0]


@app.get("/weapons", tags=["Weapons"])
def get_weapons(
    name: Optional[str] = Query(None, description="Filtrer par nom"),
    category: Optional[str] = Query(None, description="Filtrer par catégorie")
):
    """Récupère les armes avec filtres optionnels."""
    df = datasets.get("weapons")
    if df is None:
        raise HTTPException(status_code=500, detail="Dataset non disponible")
    return filter_dataframe(df, {"name": name, "category": category})


# ==================== ROOT ====================
@app.get("/", tags=["Root"])
def root():
    """Point d'entrée de l'API."""
    return {
        "message": "Bienvenue sur l'API Elden Forge",
        "documentation": "/docs",
        "endpoints": list(csv_files)
    }
