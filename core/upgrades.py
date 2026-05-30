"""Chargement + nettoyage des tables d'upgrades d'armes/boucliers (par niveau +0..+25 Standard).

Le scrap CSV utilise des dict-strings Python ({'Phy': '125 ', 'Mag': '- ', ...}).
On les parse une fois au démarrage et on expose un index `nom_arme_lower → list[UpgradeRow]`
prêt à servir en JSON (clés homogènes, valeurs numériques, '-' → 0/null).
"""
from __future__ import annotations

import ast
import csv
import os
import re
from typing import Any

from .config import DATASET_PATH, logger

# Mapping clés brutes du scrap → clés cibles homogènes avec le reste de l'app
_ATK_MAP = {"Phy": "Phy", "Mag": "Mag", "Fir": "Fire", "Lit": "Ligt", "Hol": "Holy"}
_SCALE_KEYS = ("Str", "Dex", "Int", "Fai", "Arc")
_DEF_MAP = {"Phy": "Phy", "Mag": "Mag", "Fir": "Fire", "Lit": "Ligt", "Hol": "Holy", "Bst": "Boost"}

_LEVEL_RE = re.compile(r"\+\s*(\d+)")


def _parse_dict(s: str) -> dict[str, str]:
    if not s:
        return {}
    try:
        return ast.literal_eval(s)
    except (ValueError, SyntaxError):
        return {}


def _to_float(v: Any) -> float:
    if v is None:
        return 0.0
    s = str(v).strip()
    if not s or s == "-":
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _level_of(upgrade: str) -> int:
    """'Standard ' → 0 ; 'Standard +5 ' → 5."""
    m = _LEVEL_RE.search(upgrade or "")
    return int(m.group(1)) if m else 0


def _build_attack(d: dict[str, str]) -> dict[str, float]:
    return {dst: _to_float(d.get(src)) for src, dst in _ATK_MAP.items()}


def _build_scaling(d: dict[str, str]) -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for k in _SCALE_KEYS:
        v = (d.get(k) or "").strip()
        out[k] = None if (not v or v == "-") else v
    return out


def _build_guard(d: dict[str, str]) -> dict[str, float]:
    return {dst: _to_float(d.get(src)) for src, dst in _DEF_MAP.items()}


def _load_one(filename: str, weapon_col: str) -> dict[str, list[dict]]:
    """Charge un fichier d'upgrades et renvoie {nom_arme_lower: [rows triés par level]}."""
    path = os.path.join(DATASET_PATH, filename)
    by_name: dict[str, list[dict]] = {}
    if not os.path.exists(path):
        logger.warning(f"Upgrades '{filename}' non trouvé: {path}")
        return by_name
    with open(path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            upgrade = r.get("upgrade") or ""
            level = _level_of(upgrade)
            attack = _build_attack(_parse_dict(r.get("attack power") or ""))
            scaling = _build_scaling(_parse_dict(r.get("stat scaling") or ""))
            guard = _build_guard(_parse_dict(r.get("damage reduction (%)") or ""))
            name = r.get(weapon_col) or ""
            by_name.setdefault(name.lower().strip(), []).append(
                {"level": level, "upgrade": upgrade.strip(), "attack": attack, "scaling": scaling, "guard": guard}
            )
    for rows in by_name.values():
        rows.sort(key=lambda x: x["level"])
    logger.info(f"Upgrades '{filename}' : {len(by_name)} armes, "
                f"{sum(len(v) for v in by_name.values())} lignes")
    return by_name


weapons_upgrades_by_name: dict[str, list[dict]] = _load_one("weapons_upgrades.csv", "weapon name")
shields_upgrades_by_name: dict[str, list[dict]] = _load_one("shields_upgrades.csv", "shield name")


def upgrades_for(weapon_name: str, kind: str = "weapon") -> list[dict]:
    """Renvoie les lignes d'upgrades pour un nom d'arme (case-insensitive). [] si introuvable."""
    src = weapons_upgrades_by_name if kind == "weapon" else shields_upgrades_by_name
    return src.get((weapon_name or "").lower().strip(), [])
