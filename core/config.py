import logging
import os
import pandas as pd

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

# Chemin vers les datasets
DATASET_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Dataset")

# Liste des fichiers CSV disponibles
csv_files = [
    "ammos", "armors", "ashes", "ashesOfWar", "bosses", "classes", "creatures",
    "incantations", "items", "locations", "npcs", "shields",
    "sorceries", "spirits", "talismans", "weapons"
]

# Chargement des données CSV
datasets = {}

logger.info("Chargement des datasets...")
for csv_name in csv_files:
    file_path = os.path.join(DATASET_PATH, f"{csv_name}.csv")
    if os.path.exists(file_path):
        datasets[csv_name] = pd.read_csv(file_path)
        datasets[csv_name] = datasets[csv_name].where(datasets[csv_name].notnull(), None)
        logger.info(f"Dataset '{csv_name}' chargé: {len(datasets[csv_name])} entrées")
    else:
        logger.warning(f"Dataset '{csv_name}' non trouvé: {file_path}")
logger.info(f"Chargement terminé: {len(datasets)} datasets chargés")
