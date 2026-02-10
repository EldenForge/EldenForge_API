import pandas as pd
from .config import logger


def filter_dataframe(df: pd.DataFrame, filters: dict) -> list:
    """Filtre un DataFrame selon les paramètres fournis."""
    result = df.copy()
    active_filters = {k: v for k, v in filters.items() if v is not None}
    if active_filters:
        logger.info(f"Filtres appliqués: {active_filters}")
    for key, value in filters.items():
        if value is not None and key in result.columns:
            result = result[result[key].astype(str).str.contains(str(value), case=False, na=False)]
    logger.info(f"Résultats après filtrage: {len(result)} entrées")
    return result.to_dict(orient="records")
